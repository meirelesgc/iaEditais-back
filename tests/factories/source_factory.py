import factory

from iaEditais.models.source_model import CreateSource


class CreateSourceFactory(factory.Factory):
    class Meta:
        model = CreateSource

    name = factory.Faker('company')
    description = factory.Faker('catch_phrase')
