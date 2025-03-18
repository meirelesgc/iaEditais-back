# Árvore de Verificação  

A **árvore** do **iaEditais** é uma estrutura organizada que padroniza a validação e revisão de editais, tornando o processo mais eficiente e estruturado. 🌳  

## Tipificação 🧵

Cada **árvore** é baseada em uma **tipificação** 🧵, que possui um título e pode estar vinculada a uma fonte específica, como uma lei ou norma interna. Essa tipificação também está associada ao edital, garantindo coerência na análise.  

```mermaid
graph TD
    A1[Contratação Direta]
    A2[Contratação de Solução de TIC]
    A3[Serviços com Dedicação Exclusiva de Mão de Obra]

    A1 -->|Base legal| B1[Lei nº 14.133/2021, IN Seges 65/2021]
    A2 -->|Base legal| B2[Lei nº 14.133/2021, IN SGD/ME nº 94/2022]
    A3 -->|Base legal| B3[Lei nº 14.133/2021]
    A3 -->|Jurisprudência| C1[Acórdão TCU 1207/2024]
```

## Taxonomia 🪢

No segundo nível, chamado **taxonomia**, cada item contém um nome, uma descrição, uma subfonte (opcional) e seus respectivos ramos (*branches*), que estruturam a segmentação da análise.

```mermaid
graph TD
    A[Taxonomia] -->|Contém| B[Descrição] -->|Baseado em| C[Base Normativa]

    A1[Orçamento Estimado da Contratação] -->|Inclui| A2[Informações sobre Valor Estimado e Formação de Preços]
    A2 -->|Referência| A3[Art. 6º, inciso XXXI da Lei nº 14.133/2021]

    A5[Forma Eletrônica] -->|Definido por| A6[Uso de Meio Eletrônico]
    A6 -->|Subfonte| A7[N/A]

    A9[Designação de Agentes] -->|Abrange| A10[Critérios para Escolha de Responsáveis]
    A10 -->|Referência| A11[Art. 25, §9º, da Lei nº 14.133/2021, Decreto nº 11.430/2023]
```

## Ramificações 🪡

As **ramificações** representam subdivisões específicas dos temas a serem analisados. Localizadas na extremidade da árvore, contêm descrições detalhadas dos aspectos do edital que precisam ser verificados. Aqui, você deve adicionar as questões que serão submetidas ao modelo, recebendo um retorno positivo, negativo e um feedback.  

```mermaid
graph TD
    A[Ramo] -->|Define| B[Descrição]

    A1[Critérios para Definição do Orçamento] -->|Determina| B1[As referências de preços foram corretamente utilizadas?]
    A2[Impacto na Modalidade de Contratação] -->|Analisa| B2[O orçamento impacta a escolha da modalidade licitatória?]
    A3[Adequação ao Mercado] -->|Verifica| B3[O orçamento reflete os valores praticados no mercado?]
```

## Exemplo Completo 🌳

Abaixo, segue um exemplo consolidado da árvore de verificação em sua totalidade, representando o fluxo desde a tipificação até as ramificações finais:

```mermaid
graph TD
    subgraph Tipificação
        A1[Lei nº 14.133/2021, IN Seges 65/2021]
        A[Comum a Todas as Contratações]
    end

    subgraph Taxonomia
        B[Orçamento estimado da contratação]
        B1[Informações sobre o valor estimado da contratação e formação de preços]
        B2[Artigo 6º, inciso XXXI da Lei nº 14.133/2021]
    end

    subgraph Ramo-1
        C[Critérios para Definição do Orçamento]
        C1[As referências de preços foram corretamente utilizadas?]
    end

    subgraph Ramo-2
        D[Impacto na Modalidade de Contratação]
        D1[O orçamento impacta a escolha da modalidade licitatória?]
    end

    Tipificação --> Taxonomia
    Taxonomia --> Ramo-1
    Taxonomia --> Ramo-2
```  

Esse modelo fornece um bom referencial para a análise dos editais 🚀
