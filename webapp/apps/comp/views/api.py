from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import s3like

from webapp.apps.users.models import Project

from webapp.apps.comp.compute import Compute
from webapp.apps.comp.exceptions import AppError, ValidationError
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Simulation
from webapp.apps.comp.parser import APIParser
from webapp.apps.comp.permissions import RequiresActive, RequiresPayment
from webapp.apps.comp.serializers import (
    SimulationSerializer,
    InputsSerializer,
    OutputsSerializer,
)
from webapp.apps.comp.submit import handle_submission, BadPost, APISubmit

from .core import GetOutputsObjectMixin, RecordOutputsMixin, AbstractRouterView


class InputsAPIView(APIView):
    queryset = Project.objects.all()

    def get_inputs(self, kwargs, meta_parameters=None):
        project = get_object_or_404(
            self.queryset,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
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
        meta_parameters, model_parameters = ioutils.displayer.package_defaults()
        return Response(
            {"meta_parameters": meta_parameters, "model_parameters": model_parameters}
        )

    def get(self, request, *args, **kwargs):
        print("sim api method=GET", request.GET, kwargs)
        return self.get_inputs(kwargs)

    def post(self, request, *args, **kwargs):
        print("sim api method=GET", request.GET, kwargs)
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


class BaseCreateAPIView(APIView):
    queryset = Project.objects.all()

    def post(self, request, *args, **kwargs):
        compute = Compute()
        project = get_object_or_404(
            self.queryset,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        ioutils = get_ioutils(project, Parser=APIParser)

        try:
            result = handle_submission(
                request, project, ioutils, compute, submit_class=APISubmit
            )
        except AppError as ae:
            try:
                send_mail(
                    f"COMP AppError",
                    (
                        f"An error has occurred:\n {ae.parameters}\n causing: "
                        f"{ae.traceback}\n user:{request.user.username}\n "
                        f"project: {project.app_url}."
                    ),
                    "henrymdoupe@gmail.com",
                    ["henrymdoupe@gmail.com"],
                    fail_silently=True,
                )
            # Http 401 exception if mail credentials are not set up.
            except Exception as e:
                pass

            return Response(ae.traceback, status=status.HTTP_400_BAD_REQUEST)

        # case where validation failed
        if isinstance(result, BadPost):
            return result.http_response

        # No errors--submit to model
        if result.save is not None:
            sim = SimulationSerializer(result.save.runmodel_instance)
            return Response(sim.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                result.submit.model.errors_warnings, status=status.HTTP_400_BAD_REQUEST
            )


class RequiresLoginAPIView(BaseCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive,)


class RequiresPmtAPIView(BaseCreateAPIView):
    permission_classes = (IsAuthenticatedOrReadOnly & RequiresActive & RequiresPayment,)


class APIRouterView(AbstractRouterView):
    payment_view = RequiresPmtAPIView
    login_view = RequiresLoginAPIView
    projects = Project.objects.all()


class DetailAPIView(GetOutputsObjectMixin, APIView):
    model = Simulation

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(
            kwargs["model_pk"], kwargs["username"], kwargs["title"]
        )
        sim = SimulationSerializer(self.object)
        if self.object.outputs:
            data = sim.data
            outputs = {"downloadable": data["outputs"]["outputs"]["downloadable"]}
            data["outputs"] = s3like.read_from_s3like(outputs)
            return Response(data, status=status.HTTP_200_OK)
        elif self.object.traceback is not None:
            return Response(sim.data, status=status.HTTP_200_OK)

        job_id = str(self.object.job_id)
        compute = Compute()
        try:
            job_ready = compute.results_ready(job_id)
        except JobFailError as jfe:
            self.object.traceback = ""
            self.object.save()
            return Response(
                {"error": "model error"}, status=status.HTTP_400_BAD_REQUEST
            )
        # something happened and the exception was not caught
        if job_ready == "FAIL":
            result = compute.get_results(job_id)
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

        return Response(sim.data, status=status.HTTP_202_ACCEPTED)


class OutputsAPIView(RecordOutputsMixin, APIView):
    """
    API endpoint used by the workers to update the Simulation object with the
    simulation results.
    """

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
