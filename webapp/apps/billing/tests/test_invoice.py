from datetime import timedelta

import pytest

from django.utils import timezone
from django.db.models import F, Sum

from webapp.settings import USE_STRIPE
from webapp.apps.billing import invoice

from webapp.apps.comp.models import Simulation
from webapp.apps.users.models import Deployment, Project, Profile, EmbedApproval
from webapp.apps.users.tests.utils import mock_post_to_cluster


def round4(val):
    return round(val, 4)


def sim_time_sum(simulations):
    return round4(simulations.aggregate(Sum("run_time"))["run_time__sum"])


def deployment_time_sum(deployments):
    res = 0
    for deployment in deployments.all():
        res += (deployment.deleted_at - deployment.created_at).seconds
    return round4(res)


def gen_simulations(owner, sponsor, project, run_times):
    results = []
    for run_time in run_times:
        sim = Simulation.objects.new_sim(owner.user, project, inputs_status="SUCCESS",)
        sim.run_time = run_time
        sim.sponsor = sponsor
        sim.status = "SUCCESS"
        sim.save()
        results.append(sim)

    qs = Simulation.objects.filter(owner=owner, sponsor=sponsor, project=project)
    assert qs.count() == len(run_times)

    return qs


def gen_deployments(owner, embed_approval, project, run_times):
    with mock_post_to_cluster():
        results = []
        for i, run_time in enumerate(run_times):
            deployment, _ = Deployment.objects.get_or_create_deployment(
                project, f"test-{i}", owner=owner, embed_approval=embed_approval
            )
            deployment.status = "terminated"
            deployment.created_at = timezone.now() - timedelta(seconds=run_time)
            deployment.deleted_at = timezone.now()
            deployment.save()
            results.append(deployment)

    qs = Deployment.objects.filter(
        owner=owner, embed_approval=embed_approval, project=project
    )
    assert qs.count() == len(run_times)

    return qs


@pytest.fixture
def owner_sims(profile):
    """
    Generate simulations owned by profile that is being tested.
    """
    project = Project.objects.get(title="Used-for-testing")
    return gen_simulations(
        owner=profile, sponsor=None, project=project, run_times=[60] * 10
    )


@pytest.fixture
def other_profiles_sims():
    """
    Generate simulations owned by a profile that is NOT the one that
    is primarily being tested.
    """
    project = Project.objects.get(title="Used-for-testing")
    modeler = Profile.objects.get(user__username="modeler")
    return gen_simulations(
        owner=modeler, sponsor=None, project=project, run_times=[45] * 8
    )


@pytest.fixture
def sponsored_sims(profile):
    """
    Generate simulations sponsored by a profile that is not the one being tested.
    """
    sponsored_project = Project.objects.get(title="Used-for-testing-sponsored-apps")
    return gen_simulations(
        owner=profile,
        sponsor=sponsored_project.sponsor,
        project=sponsored_project,
        run_times=[60] * 20,
    )


@pytest.fixture
def deployments(profile):
    """
    Generate deployments where the owner is the primary one being tested.
    """
    viz_project = Project.objects.get(title="Test-Viz")
    return gen_deployments(
        owner=profile, embed_approval=None, project=viz_project, run_times=[60] * 10
    )


@pytest.fixture
def ea_deployments(profile):
    """
    Generate deployments with embed approvals where the owner is the primary
    one being tested.
    """
    viz_project = Project.objects.get(title="Test-Viz")
    ea = EmbedApproval.objects.create(
        project=viz_project,
        owner=profile,
        url="https://test.compute.studio",
        name="my-embed",
    )
    return gen_deployments(
        owner=profile, embed_approval=ea, project=viz_project, run_times=[60] * 10
    )


@pytest.mark.requires_stripe
class TestInvoice:
    def test_owner_resources(
        self,
        profile,
        owner_sims,
        other_profiles_sims,
        sponsored_sims,
        deployments,
        ea_deployments,
    ):
        start = timezone.now() - timedelta(days=7)
        end = timezone.now()

        profile_invoices = invoice.invoice_customer(
            profile.user.customer, start, end, send_invoice=USE_STRIPE
        )

        owner_sims_cost = round4(
            sim_time_sum(owner_sims) * owner_sims.first().project.server_cost / 3600
        )
        owner_deployments_cost = round4(
            deployment_time_sum(deployments)
            * deployments.first().project.server_cost
            / 3600
        )
        ea_deployments_cost = round4(
            deployment_time_sum(ea_deployments)
            * ea_deployments.first().project.server_cost
            / 3600
        )

        assert profile_invoices["summary"] == {
            "deployments": {
                "embed_approval": {
                    "modeler/Test-Viz": {
                        "n": ea_deployments.count(),
                        "total_cost": ea_deployments_cost,
                        "total_time": round4(deployment_time_sum(ea_deployments) / 60),
                    }
                },
                "owner": {
                    "modeler/Test-Viz": {
                        "n": deployments.count(),
                        "total_cost": owner_deployments_cost,
                        "total_time": round4(deployment_time_sum(deployments) / 60),
                    }
                },
            },
            "simulations": {
                "owner": {
                    "modeler/Used-for-testing": {
                        "n": owner_sims.count(),
                        "total_cost": owner_sims_cost,
                        "total_time": round4(sim_time_sum(owner_sims) / 60),
                    }
                },
                "sponsor": {},
            },
        }

        stripe_invoice = profile_invoices["invoice"]

        assert profile_invoices["invoice"].amount_due == int(
            100 * (owner_sims_cost + owner_deployments_cost + ea_deployments_cost)
        )

        assert len(stripe_invoice.lines.data) == 3

        for line in stripe_invoice.lines.data:
            if (
                line.metadata.project == "modeler/Test-Viz"
                and line.metadata.description == "embedded deployments"
            ):
                assert line.amount == int(100 * ea_deployments_cost)
            elif (
                line.metadata.project == "modeler/Test-Viz"
                and line.metadata.description == "sponsored deployments"
            ):
                assert line.amount == int(100 * owner_deployments_cost)
            elif line.metadata.project == "modeler/Used-for-testing":
                assert line.amount == int(100 * owner_sims_cost)
            else:
                raise ValueError(f"{line.name} {line.metadata}")

    def test_sponsor_resources(
        self,
        profile,
        owner_sims,
        other_profiles_sims,
        sponsored_sims,
        deployments,
        ea_deployments,
    ):
        start = timezone.now() - timedelta(days=7)
        end = timezone.now()
        sponsor = Profile.objects.get(user__username="sponsor")
        profile_invoices = invoice.invoice_customer(
            sponsor.user.customer, start, end, send_invoice=USE_STRIPE
        )

        sponsored_sims_cost = round4(
            sim_time_sum(sponsored_sims)
            * sponsored_sims.first().project.server_cost
            / 3600
        )

        assert profile_invoices["summary"] == {
            "deployments": {"embed_approval": {}, "owner": {},},
            "simulations": {
                "owner": {},
                "sponsor": {
                    "modeler/Used-for-testing-sponsored-apps": {
                        "n": sponsored_sims.count(),
                        "total_cost": sponsored_sims_cost,
                        "total_time": round4(sim_time_sum(sponsored_sims) / 60),
                    }
                },
            },
        }

        stripe_invoice = profile_invoices["invoice"]

        assert profile_invoices["invoice"].amount_due == int(100 * sponsored_sims_cost)

        assert len(stripe_invoice.lines.data) == 1

        for line in stripe_invoice.lines.data:
            if line.metadata.project == "modeler/Used-for-testing-sponsored-apps":
                assert line.amount == int(100 * sponsored_sims_cost)
            else:
                raise ValueError(f"{line.name} {line.metadata}")

    def test_other_profile_resources(
        self,
        profile,
        owner_sims,
        other_profiles_sims,
        sponsored_sims,
        deployments,
        ea_deployments,
    ):
        start = timezone.now() - timedelta(days=7)
        end = timezone.now()
        modeler = Profile.objects.get(user__username="modeler")
        profile_invoices = invoice.invoice_customer(
            modeler.user.customer, start, end, send_invoice=USE_STRIPE
        )

        other_profiles_sims_cost = round4(
            sim_time_sum(other_profiles_sims)
            * other_profiles_sims.first().project.server_cost
            / 3600
        )

        assert profile_invoices["summary"] == {
            "deployments": {"embed_approval": {}, "owner": {},},
            "simulations": {
                "owner": {
                    "modeler/Used-for-testing": {
                        "n": other_profiles_sims.count(),
                        "total_cost": other_profiles_sims_cost,
                        "total_time": round4(sim_time_sum(other_profiles_sims) / 60),
                    }
                },
                "sponsor": {},
            },
        }

        stripe_invoice = profile_invoices["invoice"]

        assert profile_invoices["invoice"].amount_due == int(
            100 * other_profiles_sims_cost
        )

        assert len(stripe_invoice.lines.data) == 1

        for line in stripe_invoice.lines.data:
            if line.metadata.project == "modeler/Used-for-testing":
                assert line.amount == int(100 * other_profiles_sims_cost)
            else:
                raise ValueError(f"{line.name} {line.metadata}")
