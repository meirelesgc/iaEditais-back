import factory

from iaEditais.models.typification_model import CreateTypification


class CreateTypificationFactory(factory.Factory):
    class Meta:
        model = CreateTypification

    name = factory.Faker('word')
    description = factory.Faker('sentence')
