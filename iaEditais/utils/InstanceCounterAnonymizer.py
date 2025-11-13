from typing import Dict

from presidio_anonymizer.operators import Operator, OperatorType


class InstanceCounterAnonymizer(Operator):
    REPLACING_FORMAT = '<{entity_type}_{index}>'

    def operate(self, text: str, params: Dict = None) -> str:
        entity_type: str = params['entity_type']

        entity_mapping: Dict[Dict:str] = params['entity_mapping']

        entity_mapping_for_type = entity_mapping.get(entity_type)
        if not entity_mapping_for_type:
            new_text = self.REPLACING_FORMAT.format(
                entity_type=entity_type, index=0
            )
            entity_mapping[entity_type] = {}

        else:
            if text in entity_mapping_for_type:
                return entity_mapping_for_type[text]

            previous_index = self._get_last_index(entity_mapping_for_type)
            new_text = self.REPLACING_FORMAT.format(
                entity_type=entity_type, index=previous_index + 1
            )

        entity_mapping[entity_type][text] = new_text
        return new_text

    @staticmethod
    def _get_last_index(entity_mapping_for_type: Dict) -> int:
        """Get the last index for a given entity type."""
        if not entity_mapping_for_type:
            return -1

        # Extrair índices dos identificadores existentes
        indices = []
        for identifier in entity_mapping_for_type.values():
            # Formato: <ENTITY_TYPE_INDEX>
            if identifier.startswith('<') and identifier.endswith('>'):
                try:
                    # Extrair número após último underscore
                    parts = identifier[1:-1].split('_')
                    if len(parts) >= 2:
                        index = int(parts[-1])
                        indices.append(index)
                except ValueError:
                    continue

        return max(indices) if indices else -1

    def validate(self, params: Dict = None) -> None:
        if 'entity_mapping' not in params:
            raise ValueError(
                'An input Dict called `entity_mapping` is required.'
            )
        if 'entity_type' not in params:
            raise ValueError('An entity_type param is required.')

    def operator_name(self) -> str:
        return 'entity_counter'

    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize
