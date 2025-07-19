import uuid
from datetime import datetime

import factory

from iaEditais.models.doc import CreateDoc, Doc, Release


class CreateDocFactory(factory.Factory):
    class Meta:
        model = CreateDoc

    name = factory.Faker('word')
    typification = factory.LazyFunction(lambda: [uuid.uuid4()])


class DocFactory(factory.Factory):
    class Meta:
        model = Doc

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker('word')
    typification = factory.LazyFunction(lambda: [uuid.uuid4()])
    created_at = factory.LazyFunction(datetime.now)
    updated_at = None


class ReleaseFactory(factory.Factory):
    class Meta:
        model = Release

    id = factory.LazyFunction(uuid.uuid4)
    doc_id = factory.LazyFunction(uuid.uuid4)
    taxonomy = factory.LazyFunction(list)
    created_at = factory.LazyFunction(datetime.now)
