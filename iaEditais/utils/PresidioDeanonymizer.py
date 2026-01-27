from typing import Dict

from presidio_anonymizer import DeanonymizeEngine, OperatorConfig
from presidio_anonymizer.entities import OperatorResult

from iaEditais.utils.InstanceCounterDeanonymizer import (
    InstanceCounterDeanonymizer,
)


class PresidioDeanonymizer:
    def __init__(self):
        self.engine = DeanonymizeEngine()

        self.engine.add_deanonymizer(InstanceCounterDeanonymizer)

    def _deanonymize_presidio_entities(
        self, text: str, presidio_mapping: Dict
    ) -> str:
        if not presidio_mapping:
            return text

        anonymized_entities = []

        for entity_type, entities in presidio_mapping.items():
            for original_text, anonymized_identifier in entities.items():
                start_pos = 0
                while True:
                    pos = text.find(anonymized_identifier, start_pos)
                    if pos == -1:
                        break

                    anonymized_entities.append(
                        OperatorResult(
                            start=pos,
                            end=pos + len(anonymized_identifier),
                            entity_type=entity_type,
                        )
                    )
                    start_pos = pos + 1

        if not anonymized_entities:
            return text

        deanonymized_result = self.engine.deanonymize(
            text=text,
            entities=anonymized_entities,
            operators={
                'DEFAULT': OperatorConfig(
                    'entity_counter_deanonymizer',
                    params={'entity_mapping': presidio_mapping},
                )
            },
        )
        return deanonymized_result.text

    def deanonymize_feedback_object(
        self, feedback_obj: Dict, presidio_mapping: Dict
    ) -> Dict:
        result = feedback_obj.copy()

        if 'feedback' in result:
            result['feedback'] = self._deanonymize_presidio_entities(
                result['feedback'], presidio_mapping
            )

        return result
