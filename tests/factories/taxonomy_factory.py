from uuid import uuid4

import factory

from iaEditais.models.taxonomy_model import CreateTaxonomy


class CreateTaxonomyFactory(factory.Factory):
    class Meta:
        model = CreateTaxonomy

    typification_id = factory.LazyFunction(uuid4)
    title = factory.Faker('job')
    description = factory.Faker('sentence')
    source = factory.LazyFunction(lambda: [])
