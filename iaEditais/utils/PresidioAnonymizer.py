# Importações necessárias do Presidio

from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

from iaEditais.utils.InstanceCounterAnonymizer import InstanceCounterAnonymizer


class PresidioAnonymizer:
    """
    Classe para anonimização de texto usando Microsoft Presidio
    com reconhecedores recognizers para dados brasileiros.
    """

    def __init__(self):
        """Inicializa o anonimizador Presidio com recognizers customizados."""
        self.analyzer = self._setup_analyzer()
        # Cria o motor de anonimização
        self.engine = AnonymizerEngine()
        # Adiciona o operador de contagem de entidades
        self.engine.add_anonymizer(InstanceCounterAnonymizer)

        # Mapeamentos persistentes para consistência entre chunks
        self.existing_presidio_mapping = {}

    def _setup_analyzer(self):
        """Configura o analisador com reconhecedores customizados para dados brasileiros."""

        # Padrão regex para CPF
        cpf_pattern = Pattern(
            name='cpf_pattern',
            regex=r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',
            score=1,
        )

        # Padrão regex para CNPJ
        cnpj_pattern = Pattern(
            name='cnpj_pattern',
            regex=r'\b\d{2}\.?\d{3}\.?\d{3}/\d{4}-\d{2}\b',
            score=1,
        )

        # Padrão regex para RG
        rg_pattern = Pattern(
            name='rg_pattern',
            regex=r'\b\d{2}\.?\d{3}\.?\d{3}-?\d{1,2}\b',
            score=1,
        )

        # Padrão regex para números de celular brasileiro
        celular_pattern = Pattern(
            name='celular_pattern',
            regex=r'\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b',
            score=1,
        )

        # Padrão para valores em reais
        valor_reais_pattern = Pattern(
            name='valor_reais_pattern',
            regex=r'R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}',
            score=1,
        )

        # Padrão para números de processos
        numero_processo_pattern = Pattern(
            name='numero_processo_pattern',
            regex=r'\b\d+\.\d+/\d{4}-\d{2}\b',
            score=1,
        )

        # Padrão para números de editais da fiocruz
        numero_edital_pattern = Pattern(
            name='numero_edital_pattern',
            regex=r'\b\d{2,5}/\d{4}\b',
            score=1,
        )

        # Padrão para email
        email_pattern = Pattern(
            name='email_pattern',
            regex=r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            score=1,
        )

        data_pattern = Pattern(
            name='data_pattern',
            regex=r'\b(0?[1-9]|[12][0-9]|3[01])/(0?[1-9]|1[0-2])/\d{4}\b',
            score=1,
        )

        # Padrão para horas
        hora_pattern = Pattern(
            name='hora_pattern',
            regex=r'\b([01]\d|2[0-3]):[0-5]\d\b',
            score=1,
        )

        # Padrão para CEP
        cep_pattern = Pattern(
            name='cep_pattern', regex=r'\b\d{5}-?\d{3}\b', score=1
        )

        # Reconhecedor customizado para CPF
        custom_recognizer_cpf = PatternRecognizer(
            supported_entity='CPF',
            patterns=[cpf_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para CNPJ
        custom_recognizer_cnpj = PatternRecognizer(
            supported_entity='CNPJ',
            patterns=[cnpj_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para RG
        custom_recognizer_rg = PatternRecognizer(
            supported_entity='RG',
            patterns=[rg_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para celular
        custom_recognizer_celular = PatternRecognizer(
            supported_entity='PHONE_NUMBER_BR',
            patterns=[celular_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para valores em reais
        custom_recognizer_valor_reais = PatternRecognizer(
            supported_entity='MONEY',
            patterns=[valor_reais_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para números de processos
        custom_recognizer_numero_processo = PatternRecognizer(
            supported_entity='PROCESS_NUMBER',
            patterns=[numero_processo_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para números de editais da fiocruz
        custom_recognizer_numero_edital = PatternRecognizer(
            supported_entity='EDITAL_NUMBER',
            patterns=[numero_edital_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para email
        custom_recognizer_email = PatternRecognizer(
            supported_entity='EMAIL_ADDRESS',
            patterns=[email_pattern],
            supported_language='pt',
        )

        custom_recognizer_data = PatternRecognizer(
            supported_entity='DATE',
            patterns=[data_pattern],
            supported_language='pt',
        )

        custom_recognizer_hora = PatternRecognizer(
            supported_entity='TIME',
            patterns=[hora_pattern],
            supported_language='pt',
        )

        custom_recognizer_cep = PatternRecognizer(
            supported_entity='ZIP_CODE',
            patterns=[cep_pattern],
            supported_language='pt',
        )

        # Reconhecedor customizado para instituições
        institutions_list = [
            'FIOCRUZ',
            'Fundação Oswaldo Cruz',
            'Instituto  Nacional  de  Saúde  da  Mulher,  da  Criança  e  do Adolescente Fernandes Figueira',
            'Ministério da Saúde/ANVISA',
            'Fiocruz',
            'fiocruz',
        ]

        # Reconhecedor customizado para instituições
        custom_recognizer_institutions = PatternRecognizer(
            supported_entity='INSTITUTION',
            deny_list=institutions_list,
            supported_language='pt',
        )

        # Configuração do motor NLP para português
        configuration = {
            'nlp_engine_name': 'spacy',
            'models': [{'lang_code': 'pt', 'model_name': 'pt_core_news_lg'}],
        }

        # Criação do provedor do motor NLP
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine_with_portuguese = provider.create_engine()

        # Criação do AnalyzerEngine com suporte ao português
        analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine_with_portuguese, supported_languages=['pt']
        )

        # Remove reconhecedores pré-definidos
        recognizers = analyzer.registry.get_recognizers(
            language='pt', all_fields=True
        )
        for recognizer in recognizers:
            analyzer.registry.remove_recognizer(recognizer.name)

        # Adiciona reconhecedores customizados ao registry
        analyzer.registry.add_recognizer(custom_recognizer_celular)
        analyzer.registry.add_recognizer(custom_recognizer_cpf)
        analyzer.registry.add_recognizer(custom_recognizer_cnpj)
        analyzer.registry.add_recognizer(custom_recognizer_rg)
        analyzer.registry.add_recognizer(custom_recognizer_institutions)
        analyzer.registry.add_recognizer(custom_recognizer_valor_reais)
        analyzer.registry.add_recognizer(custom_recognizer_numero_processo)
        analyzer.registry.add_recognizer(custom_recognizer_numero_edital)
        analyzer.registry.add_recognizer(custom_recognizer_email)
        analyzer.registry.add_recognizer(custom_recognizer_data)
        analyzer.registry.add_recognizer(custom_recognizer_hora)
        analyzer.registry.add_recognizer(custom_recognizer_cep)

        # Remoção de alguns recognizers para evitar falsos positivos
        # analyzer.registry.remove_recognizer("PhoneRecognizer")
        # analyzer.registry.remove_recognizer("UrlRecognizer")
        # analyzer.registry.remove_recognizer("IpRecognizer")

        return analyzer

    def _anonymize_text(self, text, verbose=False, existing_mapping=None):
        """
        Anonimiza o texto usando Presidio.

        Args:
            text (str): Texto a ser anonimizado
            verbose (bool): Se True, imprime informações de debug
            existing_mapping (dict): Mapeamento existente para manter consistência

        Returns:
            tuple: (texto_anonimizado, mapeamento_entidades)
        """
        results_portuguese = self.analyzer.analyze(text=text, language='pt')

        if verbose:
            print(f'Texto a ser anonimizado: {text}')

        # Usar mapeamento existente ou criar novo
        entity_mapping = (
            existing_mapping.copy() if existing_mapping else dict()
        )

        anonymization_result = self.engine.anonymize(
            text=text,
            analyzer_results=results_portuguese,
            operators={
                'DEFAULT': OperatorConfig(
                    'entity_counter', {'entity_mapping': entity_mapping}
                )
            },
        )

        if verbose:
            print(f'Texto anonimizado: {anonymization_result.text}')
            print(f'Mapeamento de entidades: {entity_mapping}')

        return anonymization_result.text, entity_mapping

    def anonymize_chunks(
        self,
        chunks: list[Document],
        verbose=False,
    ):
        """
        Anonimiza os chunks usando Presidio.
        """

        for index, chunk in enumerate(chunks):
            if verbose:
                print(f'Anonimizando chunk {index}')

            anonymized_text, entity_mapping = self._anonymize_text(
                chunk.page_content, verbose, self.existing_presidio_mapping
            )
            self.existing_presidio_mapping.update(entity_mapping)
            chunk.page_content = anonymized_text
            chunk.metadata['presidio_mapping'] = entity_mapping
            chunk.metadata['anonymized'] = True

        return chunks
