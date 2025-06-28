from uuid import uuid4

import factory

from iaEditais.models.branch_model import CreateBranch


class CreateBranchFactory(factory.Factory):
    class Meta:
        model = CreateBranch

    taxonomy_id = factory.LazyFunction(uuid4)
    title = factory.Faker('word')
    description = factory.Faker('text')
