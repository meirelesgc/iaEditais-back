from uuid import uuid4

import factory

from iaEditais.models import user_units


class CreateUserUnitFactory(factory.Factory):
    class Meta:
        model = user_units.CreateUserUnit

    user_id = factory.LazyFunction(uuid4)
    unit_id = factory.LazyFunction(uuid4)
