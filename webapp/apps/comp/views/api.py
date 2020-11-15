from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import Http404

from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import IntegerField
from rest_framework import filters

import paramtools as pt
import cs_storage

from webapp.apps.users.auth import ClusterAuthentication
from webapp.apps.users.models import (
    Project,
    Profile,
    get_project_or_404,
    projects_with_access,
)
from webapp.apps.users.permissions import RequiresActive, StrictRequiresActive

from webapp.apps.comp.asyncsubmit import SubmitInputs, SubmitSim
from webapp.apps.comp.compute import Compute, JobFailError
from webapp.apps.comp.exceptions import (
    AppError,
    ValidationError,
    BadPostException,
    ForkObjectException,
    PrivateAppException,
    PrivateSimException,
    CollaboratorLimitException,
)
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Inputs, Simulation, PendingPermission, ANON_BEFORE
from webapp.apps.comp.parser import APIParser
from webapp.apps.comp.serializers import (
    SimulationSerializer,
    MiniSimulationSerializer,
    InputsSerializer,
    OutputsSerializer,
    AddAuthorsSerializer,
    SimAccessSerializer,
    PendingPermissionSerializer,
)
from webapp.apps.comp.utils import is_valid

from .core import (
    GetOutputsObjectMixin,
    RecordOutputsMixin,
    AbstractRouterAPIView,
    RequiresLoginPermissions,
    RequiresPmtPermissions,
)


class InputsAPIView(APIView):
    queryset = Project.objects.all()

    def get_inputs(self, kwargs, meta_parameters=None):
        project = get_project_or_404(
            self.queryset,
            user=self.request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        ioutils = get_ioutils(project)
        try:
            defaults = ioutils.model_parameters.defaults(meta_parameters)
        except pt.ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        if "year" in defaults["meta_parameters"]:
            defaults.update({"extend": True})
        return Response(defaults)

    def get(self, request, *args, **kwargs):
        print("inputs api method=GET", request.GET, kwargs)
        return self.get_inputs(kwargs)

    def post(self, request, *args, **kwargs):
        print("inputs api method=POST", request.POST, kwargs)
        ser = InputsSerializer(data=request.data)
        if ser.is_valid():
            data = ser.validated_data
            if "meta_parameters" in data:
                meta_parameters = data["meta_parameters"]
            else:
                meta_parameters = {}
            return self.get_inputs(kwargs, meta_parameters)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class DetailMyInputsAPIView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    queryset = Inputs.objects.all()

    def get(self, request, *args, **kwargs):
        print("myinputs api method=GET", request.GET, kwargs)
        inputs = get_object_or_404(
            self.queryset,
            sim__model_pk=kwargs["model_pk"],
            project__title__iexact=kwargs["title"],
            project__owner__user__username__iexact=kwargs["username"],
        )
        if not inputs.has_read_access(request.user):
            if not inputs.project.has_read_access(request.user):
                raise Http404()
            raise PermissionDenied()
        ser = InputsSerializer(inputs, context={"request": self.request})
        return Response(ser.data)


def submit(request, success_status, project, sim):
    compute = Compute()
    ioutils = get_ioutils(project, Parser=APIParser)

    try:
        submit_inputs = SubmitInputs(request, project, ioutils, compute, sim)
        result = submit_inputs.submit()
    except BadPostException as bpe:
        return Response(bpe.errors, status=status.HTTP_400_BAD_REQUEST)
    except AppError as ae:
        try:
            send_mail(
                f"Compute Studio AppError",
                (
                    f"An error has occurred:\n {ae.parameters}\n causing: "
                    f"{ae.traceback}\n user:{request.user.username}\n "
                    f"project: {project.app_url}."
                ),
                "notifications@compute.studio",
                ["hank@compute.studio"],
                fail_silently=True,
            )
        # Http 401 exception if mail credentials are not set up.
        except Exception:
            pass

        return Response(ae.traceback, status=success_status)

    inputs = InputsSerializer(result)

    return Response(inputs.data, status=status.HTTP_201_CREATED)


class BaseCreateAPIView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    queryset = Project.objects.all()

    def post(self, request, *args, **kwargs):
        project = get_project_or_404(
            self.queryset,
            user=request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        # Setting inputs_status="PENDING" ensures that each request
        # creates a new simulation. This is necessary if a user is submitting
        # a batch of simulations.
        sim = Simulation.objects.new_sim(request.user, project, inputs_status="PENDING")
        return submit(request, status.HTTP_201_CREATED, project, sim)


class RequiresLoginAPIView(RequiresLoginPermissions, BaseCreateAPIView):
    pass


class RequiresPmtAPIView(RequiresPmtPermissions, BaseCreateAPIView):
    pass


class CreateAPIView(AbstractRouterAPIView):
    payment_view = RequiresPmtAPIView
    login_view = RequiresLoginAPIView
    projects = Project.objects.all()


class BaseDetailAPIView(GetOutputsObjectMixin, APIView):
    model = Simulation
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.object = self.get_object(
                kwargs["model_pk"], kwargs["username"], kwargs["title"]
            )
            if self.object.has_write_access(request.user):
                serializer = MiniSimulationSerializer(
                    self.object, data=request.data, context={"request": request}
                )
                try:
                    if serializer.is_valid():
                        serializer.save(last_modified=timezone.now())

                        return Response(serializer.data)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
                except (
                    PrivateSimException,
                    CollaboratorLimitException,
                    PrivateAppException,
                ) as e:
                    return Response(
                        {e.resource: e.todict()}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request, *args, **kwargs):
        print("getting objects", kwargs)
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        print("got self.object", self.object)
        if not self.object.has_write_access(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if self.object.status == "STARTED":
            return submit(request, status.HTTP_200_OK, self.object.project, self.object)
        else:
            return Response(
                {
                    "status": "This simulation is either pending or in a terminated state."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_sim_data(self, user, as_remote, username, title, model_pk):
        self.object = self.get_object(model_pk, username, title)
        sim = SimulationSerializer(self.object, context={"request": self.request})
        data = sim.data
        if self.object.outputs_version() == "v0":
            return Response(data, status=status.HTTP_200_OK)
        elif self.object.outputs:
            outputs = data["outputs"]["outputs"]
            if not as_remote:
                data["outputs"] = cs_storage.read(outputs)
            else:
                if self.request.is_secure():
                    protocol = "https"
                else:
                    protocol = "http"  # local dev.
                base_url = f"{protocol}://{self.request.get_host()}"
                for rem_output in data["outputs"]["outputs"]["renderable"]["outputs"]:
                    rem_output[
                        "screenshot"
                    ] = f"{base_url}/storage/screenshots/{rem_output['id']}.png"
            return Response(data, status=status.HTTP_200_OK)
        elif self.object.traceback is not None:
            return Response(data, status=status.HTTP_200_OK)
        elif self.object.status == "STARTED":
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(data, status=status.HTTP_202_ACCEPTED)

    def get(self, request, *args, **kwargs):
        return self.get_sim_data(request.user, as_remote=False, **kwargs)


class RequiresLoginDetailAPIView(RequiresLoginPermissions, BaseDetailAPIView):
    pass


class RequiresPmtDetailAPIView(RequiresPmtPermissions, BaseDetailAPIView):
    pass


class DetailAPIView(AbstractRouterAPIView):
    payment_view = RequiresPmtDetailAPIView
    login_view = RequiresLoginDetailAPIView
    projects = Project.objects.all()


class RemoteDetailAPIView(BaseDetailAPIView):
    def get(self, request, *args, **kwargs):
        return self.get_sim_data(request.user, as_remote=True, **kwargs)

    def post(self, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def put(self, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ForkDetailAPIView(RequiresLoginPermissions, GetOutputsObjectMixin, APIView):
    model = Simulation
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        try:
            sim = Simulation.objects.fork(self.object, request.user)
        except ForkObjectException as e:
            msg = str(e)
            return Response({"fork": msg}, status=status.HTTP_400_BAD_REQUEST)
        except (
            PrivateSimException,
            CollaboratorLimitException,
            PrivateAppException,
        ) as e:
            return Response(
                data={e.resource: e.todict()}, status=status.HTTP_400_BAD_REQUEST,
            )
        data = MiniSimulationSerializer(sim).data
        return Response(data, status=status.HTTP_201_CREATED)


class NewSimulationAPIView(RequiresLoginPermissions, APIView):
    projects = Project.objects.all()
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    def post(self, request, *args, **kwargs):
        project = get_project_or_404(
            self.projects,
            user=request.user,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        sim = Simulation.objects.new_sim(user=request.user, project=project)
        context = {"request": request}
        data = {
            "inputs": InputsSerializer(sim.inputs, context=context).data,
            "sim": SimulationSerializer(sim, context=context).data,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class OutputsAPIView(RecordOutputsMixin, APIView):
    """
    API endpoint used by the workers to update the Simulation object with the
    simulation results.
    """

    authentication_classes = (
        ClusterAuthentication,
        # Uncomment to allow token-based authentication for this endpoint.
        # TokenAuthentication,
    )

    def put(self, request, *args, **kwargs):
        print("myoutputs api method=PUT", kwargs)
        ser = OutputsSerializer(data=request.data)
        if ser.is_valid():
            data = ser.validated_data
            sim = get_object_or_404(
                Simulation.objects.prefetch_related("project"), job_id=data["job_id"]
            )
            if not sim.project.has_write_access(request.user):
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            if sim.status == "PENDING":
                self.record_outputs(sim, data)
                if sim.notify_on_completion:
                    try:
                        host = f"https://{request.get_host()}"
                        sim_url = f"{host}{sim.get_absolute_url()}"
                        send_mail(
                            f"{sim} has finished!",
                            (
                                f"Here's a link to your simulation:\n\n{sim_url}."
                                f"\n\nPlease write back if you have any questions or feedback!"
                            ),
                            "notifications@compute.studio",
                            [sim.owner.user.email],
                            fail_silently=True,
                        )
                    # Http 401 exception if mail credentials are not set up.
                    except Exception:
                        import traceback

                        traceback.print_exc()
                        pass
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class MyInputsAPIView(APIView):
    authentication_classes = (
        ClusterAuthentication,
        # Uncomment to allow token-based authentication for this endpoint.
        # TokenAuthentication,
    )

    def put(self, request, *args, **kwargs):
        print("myinputs api method=PUT", kwargs)
        ser = InputsSerializer(data=request.data)
        if ser.is_valid():
            data = ser.validated_data
            inputs = get_object_or_404(
                Inputs.objects.prefetch_related("project"), job_id=data["job_id"]
            )
            if not inputs.project.has_write_access(request.user):
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            if inputs.status in ("PENDING", "INVALID"):
                # successful run
                if data["status"] == "SUCCESS":
                    inputs.errors_warnings = data["errors_warnings"]
                    inputs.custom_adjustment = data.get("custom_adjustment", None)
                    inputs.status = "SUCCESS" if is_valid(inputs) else "INVALID"
                    inputs.save()
                    if inputs.status == "SUCCESS":
                        submit_sim = SubmitSim(inputs.sim, compute=Compute())
                        submit_sim.submit()
                # failed run, exception was caught
                else:
                    inputs.status = "FAIL"
                    inputs.traceback = data["traceback"]
                    inputs.save()
            return Response(status=status.HTTP_200_OK)
        else:
            print("inputs put error", ser.errors)
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthorsAPIView(RequiresLoginPermissions, GetOutputsObjectMixin, APIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    model = Simulation

    def put(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        if not self.object.has_admin_access(request.user):
            raise PermissionDenied()

        ser = AddAuthorsSerializer(data=request.data)

        if ser.is_valid():
            data = ser.validated_data
            new_authors = set(obj["username"] for obj in data["authors"])
            profiles = Profile.objects.filter(user__username__in=new_authors)
            if profiles.count() < len(new_authors):
                return Response(
                    {"authors": "All authors must have an account on Compute Studio."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for profile in profiles.all():
                if self.object.authors.filter(pk=profile.pk).count() > 0:
                    continue
                try:
                    pp, created = PendingPermission.objects.get_or_create(
                        sim=self.object, profile=profile, permission_name="add_author"
                    )
                except (
                    PrivateSimException,
                    CollaboratorLimitException,
                    PrivateAppException,
                ) as e:
                    return Response(
                        data={e.resource: e.todict()},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # PP already exists and is not expired.
                if not created and not pp.is_expired():
                    continue
                # PP exists but is expired, so delete the existing one and create a
                # new one.
                if not created and pp.is_expired():
                    pp.delete()
                    pp, created = PendingPermission.objects.get_or_create(
                        sim=self.object, profile=profile, permission_name="add_author"
                    )

                try:
                    print(data)
                    msg = next(
                        (
                            obj["msg"]
                            for obj in data["authors"]
                            if obj["username"] == str(profile)
                        ),
                        None,
                    )
                    if msg:
                        msg = f"{msg}\n\n"
                    else:
                        msg = None
                    host = f"https://{request.get_host()}"
                    sim_url = f"{host}{self.object.get_absolute_url()}"
                    send_mail(
                        f"Coauthor invite for {self.object}",
                        (
                            f"{request.user.username} has invited you to be "
                            f"a coauthor on this simulation: {sim_url}\n\n"
                            f"{msg if msg else ''}"
                            f"Please reply to this email if you have any questions."
                        ),
                        f"{str(request.user.username)} <notifications@compute.studio>",
                        [profile.user.email],
                        fail_silently=True,
                    )
                # Http 401 exception if mail credentials are not set up.
                except Exception:
                    import traceback

                    traceback.print_exc()

            return Response(
                PendingPermissionSerializer(
                    self.object.pending_permissions, many=True
                ).data,
                status=status.HTTP_200_OK,
            )
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthorsDeleteAPIView(RequiresLoginPermissions, GetOutputsObjectMixin, APIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    model = Simulation

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        profile = get_object_or_404(Profile, user__username__iexact=kwargs["author"])
        # profile = Profile.objects.get(user__username__iexact=kwargs["author"])
        if profile == self.object.owner:
            return Response(
                {
                    "error": "The owner of the simulation cannot be deleted from the authors list."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # User without write access can only remove themselves as author.
        if (
            not self.object.has_admin_access(request.user)
            and profile.user != request.user
        ):
            raise PermissionDenied()

        # if profile is in authors relation.
        if self.object.authors.filter(pk=profile.pk).count() > 0:
            self.object.authors.remove(profile)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # if profile is not added as an author, then delete the permission
        # request.
        pps = PendingPermission.objects.filter(
            sim=self.object, profile=profile, permission_name="add_author"
        )
        if pps.count() > 0:
            pps.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # if profile is not an author or has not been requested to be an
        # author, then return 404.
        return Response(status=status.HTTP_404_NOT_FOUND)


class SimulationAccessAPIView(RequiresLoginPermissions, GetOutputsObjectMixin, APIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    model = Simulation

    def put(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        if not self.object.has_admin_access(request.user):
            raise PermissionDenied()

        ser = SimAccessSerializer(data=request.data, many=True)
        if ser.is_valid():
            data = ser.validated_data
            for access_obj in data:
                user = get_object_or_404(
                    get_user_model(), username__iexact=access_obj["username"]
                )
                previous_role = self.object.role(user)
                try:
                    self.object.assign_role(access_obj["role"], user)
                except (ResourceLimitException, PrivateAppException) as e:
                    return Response(
                        data={e.resource: e.todict()},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                updated_role = self.object.role(user)
                if updated_role is not None and updated_role != previous_role:
                    try:
                        msg = access_obj.get("msg", None)
                        if msg:
                            msg = f"{msg}\n\n"
                        else:
                            msg = None

                        host = f"https://{request.get_host()}"
                        sim_url = f"{host}{self.object.get_absolute_url()}"
                        send_mail(
                            f"Updated role for {self.object}",
                            (
                                f"You have been assigned the '{updated_role}' role for this simulation: "
                                f"{sim_url}.\n\n"
                                f"{msg if msg else ''}"
                                f"\nPlease reply to this email if you have any questions."
                            ),
                            f"{request.user.username} <notifications@compute.studio>",
                            [user.email],
                            fail_silently=True,
                        )
                    # Http 401 exception if mail credentials are not set up.
                    except Exception:
                        import traceback

                        traceback.print_exc()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class SimsAPIView(generics.ListAPIView):
    permission_classes = (StrictRequiresActive,)
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )

    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["creation_date", "project__title", "project__owner"]
    ordering = ["-creation_date"]

    queryset = Simulation.objects.all()
    serializer_class = MiniSimulationSerializer


class UserSimsAPIView(SimsAPIView):
    def get_queryset(self):
        return self.queryset.filter(owner__user=self.request.user)


class PublicSimsAPIView(SimsAPIView):
    permission_classes = (RequiresActive,)
    queryset = Simulation.objects.public_sims()

    def get_queryset(self):
        return self.queryset.filter(
            creation_date__gte=ANON_BEFORE,
            project__pk__in=projects_with_access(self.request.user),
        )


class ProfileSimsAPIView(SimsAPIView):
    permission_classes = (RequiresActive,)
    queryset = Simulation.objects.public_sims()

    def get_queryset(self):
        username = self.request.parser_context["kwargs"].get("username", None)
        user = get_object_or_404(get_user_model(), username__iexact=username)
        return self.queryset.filter(
            owner__user=user, project__pk__in=projects_with_access(self.request.user),
        )
