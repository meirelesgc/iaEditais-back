import uuid
from datetime import datetime

import factory

from iaEditais.models import unit_model


class CreateUnitFactory(factory.Factory):
    class Meta:
        model = unit_model.CreateUnit

    name = factory.Faker('company')
    location = factory.Faker('city')


class UnitFactory(factory.Factory):
    class Meta:
        model = unit_model.Unit

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker('company')
    location = factory.Faker('city')
    created_at = factory.LazyFunction(datetime.now)
    updated_at = None
