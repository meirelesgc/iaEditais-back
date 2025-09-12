import factory

from iaEditais.models import (
    AccessType,
    Branch,
    Document,
    Source,
    Taxonomy,
    Typification,
    Unit,
    User,
)


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


class TypificationFactory(factory.Factory):
    class Meta:
        model = Typification

    name = factory.Sequence(lambda n: f'Tipificação de Teste {n}')


class TaxonomyFactory(factory.Factory):
    class Meta:
        model = Taxonomy

    title = factory.Sequence(lambda n: f'Taxonomia de Teste {n}')
    description = factory.Faker('paragraph', nb_sentences=3, locale='pt_BR')


class BranchFactory(factory.Factory):
    class Meta:
        model = Branch

    title = factory.Sequence(lambda n: f'Ramo de Teste {n}')
    description = factory.Faker('paragraph', nb_sentences=3, locale='pt_BR')


class DocFactory(factory.Factory):
    class Meta:
        model = Document

    name = factory.Sequence(lambda n: f'Documento de Teste {n}')
    identifier = factory.Sequence(lambda n: f'Identificador de Teste {n}')
    description = factory.Faker('paragraph', nb_sentences=3, locale='pt_BR')
