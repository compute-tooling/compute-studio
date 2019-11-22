from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import cs_storage

from webapp.apps.users.models import Project

from webapp.apps.comp.asyncsubmit import SubmitInputs, SubmitSim
from webapp.apps.comp.compute import Compute, JobFailError
from webapp.apps.comp.exceptions import AppError, ValidationError, BadPostException
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.parser import APIParser
from webapp.apps.comp.permissions import RequiresActive, RequiresPayment
from webapp.apps.comp.serializers import (
    SimulationSerializer,
    SimDescriptionSerializer,
    InputsSerializer,
    OutputsSerializer,
)
from webapp.apps.comp.utils import is_valid

from .core import GetOutputsObjectMixin, RecordOutputsMixin, AbstractRouterAPIView


class InputsAPIView(APIView):
    queryset = Project.objects.all()

    def get_inputs(self, kwargs, meta_parameters=None):
        project = get_object_or_404(
            self.queryset,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        ioutils = get_ioutils(project)
        if meta_parameters is not None:
            try:
                parsed_mp = ioutils.displayer.parsed_meta_parameters()
                ioutils.displayer.meta_parameters = parsed_mp.validate(
                    meta_parameters, throw_errors=True
                )
            except ValidationError as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        defaults = ioutils.displayer.package_defaults()
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
        if "model_pk" in kwargs:
            inputs = get_object_or_404(
                self.queryset,
                outputs__model_pk=kwargs["model_pk"],
                project__title__iexact=kwargs["title"],
                project__owner__user__username__iexact=kwargs["username"],
            )
        else:
            inputs = self.queryset.get_object_from_hashid_or_404(kwargs["hashid"])
        return Response(InputsSerializer(inputs).data)


class BaseCreateAPIView(APIView):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    queryset = Project.objects.all()

    def post(self, request, *args, **kwargs):
        compute = Compute()
        project = get_object_or_404(
            self.queryset,
            owner__user__username__iexact=kwargs["username"],
            title__iexact=kwargs["title"],
        )
        ioutils = get_ioutils(project, Parser=APIParser)

        try:
            submit_inputs = SubmitInputs(request, project, ioutils, compute)
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
                    "hank@compute.studio",
                    ["hank@compute.studio"],
                    fail_silently=True,
                )
            # Http 401 exception if mail credentials are not set up.
            except Exception:
                pass

            return Response(ae.traceback, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        inputs = InputsSerializer(result)

        return Response(inputs.data, status=status.HTTP_201_CREATED)


class RequiresLoginAPIView(BaseCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive,)


class RequiresPmtAPIView(BaseCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive & RequiresPayment,)


class APIRouterView(AbstractRouterAPIView):
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
            if self.object.owner.user == request.user:
                print("got data", request.data)
                serializer = SimDescriptionSerializer(self.object, data=request.data)
                if serializer.is_valid():
                    serializer.save(last_modified=timezone.now())
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    def get(self, request, as_remote, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        sim = SimulationSerializer(self.object)
        write_access = (
            request.user.is_authenticated
            and request.user == self.object.owner.user
        )
        data = {"write_access": write_access}
        if self.object.outputs:
            data.update(sim.data)
            outputs = data["outputs"]["outputs"]
            if not as_remote:
                data["outputs"] = cs_storage.read(outputs)
            else:
                data["outputs"]["outputs"] = cs_storage.add_screenshot_links(
                    data["outputs"]["outputs"]
                )
            return Response(data, status=status.HTTP_200_OK)
        elif self.object.traceback is not None:
            data.update(sim.data)
            return Response(data, status=status.HTTP_200_OK)

        compute = Compute()
        try:
            job_ready = compute.results_ready(self.object)
        except JobFailError:
            self.object.traceback = ""
            self.object.save()
            return Response(
                {"error": "model error"}, status=status.HTTP_400_BAD_REQUEST
            )
        # something happened and the exception was not caught
        if job_ready == "FAIL":
            result = compute.get_results(self.object)
            if result["traceback"]:
                traceback_ = result["traceback"]
            else:
                traceback_ = "Error: The traceback for this error is unavailable."
            self.object.traceback = traceback_
            self.object.status = "WORKER_FAILURE"
            self.object.save()
            return Response(
                {"error": "model error"}, status=status.HTTP_400_BAD_REQUEST
            )
        data.update(sim.data)
        return Response(data, status=status.HTTP_202_ACCEPTED)


class DetailAPIView(BaseDetailAPIView):
    def get(self, request, *args, **kwargs):
        as_remote = False
        return super().get(request, as_remote, *args, **kwargs)


class RemoteDetailAPIView(BaseDetailAPIView):
    def get(self, request, *args, **kwargs):
        as_remote = True
        return super().get(request, as_remote, *args, **kwargs)


class OutputsAPIView(RecordOutputsMixin, APIView):
    """
    API endpoint used by the workers to update the Simulation object with the
    simulation results.
    """

    authentication_classes = (TokenAuthentication,)

    def put(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.username == "comp-api-user":
            ser = OutputsSerializer(data=request.data)
            if ser.is_valid():
                data = ser.validated_data
                sim = get_object_or_404(Simulation, job_id=data["job_id"])
                if sim.status == "PENDING":
                    self.record_outputs(sim, data)
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


class MyInputsAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    def put(self, request, *args, **kwargs):
        print("myinputs api method=PUT", kwargs)

        if request.user.username == "comp-api-user":
            data = request.data
            ser = InputsSerializer(data=request.data)
            if ser.is_valid():
                data = ser.validated_data
                inputs = get_object_or_404(Inputs, job_id=data["job_id"])
                print("data")
                print(data)
                if inputs.status == "PENDING":
                    # successful run
                    if data["status"] == "SUCCESS":
                        inputs.errors_warnings = data["errors_warnings"]
                        inputs.custom_adjustment = data.get("custom_adjustment", None)
                        inputs.status = "SUCCESS" if is_valid(inputs) else "INVALID"
                        inputs.save()
                        if inputs.status == "SUCCESS":
                            submit_sim = SubmitSim(inputs, compute=Compute())
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
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
