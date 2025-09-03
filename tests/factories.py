import factory

from iaEditais.models import AccessType, Source, Unit, User


class UnitFactory(factory.Factory):
    class Meta:
        model = Unit

    name = factory.Sequence(lambda n: f'test unit {n}')
    location = factory.Faker('address')


class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'test{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    phone_number = factory.Sequence(lambda n: f'1190000{n:04d}')
    access_level = AccessType.DEFAULT
    unit_id = None


class SourceFactory(factory.Factory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f'Fonte de Teste {n}')
    description = factory.Faker('paragraph', nb_sentences=3, locale='pt_BR')
