from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.models import Inputs, Simulation


def test_get_next_model_pk(db):
    owner = Profile.objects.get(user__username="modeler")
    project = Project.objects.get(title="Used-for-testing", owner=owner)
    inputs = Inputs(inputs_style="paramtools", project=project)
    inputs.save()
    naive_next_model_pk = 1
    for sim in Simulation.objects.filter(project=project):
        if sim.model_pk >= naive_next_model_pk:
            naive_next_model_pk = sim.model_pk
    sim = Simulation(
        inputs=inputs,
        project=project,
        model_pk=Simulation.objects.next_model_pk(project),
    )
    sim.save()
    assert sim.model_pk == naive_next_model_pk
    assert Simulation.objects.next_model_pk(project) == sim.model_pk + 1
