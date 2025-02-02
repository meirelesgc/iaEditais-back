# IaEditais - Plataforma de Avaliação de Editais

Este é o README do IaEditais, uma API desenvolvida para avaliar editais utilizando modelos de linguagem de grande porte (Large Language Models - LLMs). A plataforma automatiza tanto a formatação dos critérios de avaliação quanto a avaliação dos próprios editais.

## Pré-requisitos

- Python 3.7 ou superior
- `pipx` para instalar pacotes Python isolados
- `poetry` para gerenciamento de dependências

## Instalação

1. Instale o `pipx`:
    ```sh
    pip install pipx
    ```

2. Use o `pipx` para instalar o `poetry`:
    ```sh
    pipx install poetry
    ```

3. Instale as dependências do projeto:
    ```sh
    poetry install
    ```

4. Ative o ambiente virtual:
    ```sh
    poetry shell
    ```

## Executando o Projeto

1. Execute a task principal do projeto para que ele inicie:
    ```sh
    task run
    ```

2. Acesse a documentação da API no navegador:
    [http://localhost:8000/redocs](http://localhost:8000/redocs)

3. Execute a task dos testes (Em desenvolvimento):
    ```sh
    task test
    ```
    

## Sobre o IaEditais

**IaEditais** é uma plataforma inovadora que utiliza modelos de linguagem de grande porte para otimizar o processo de avaliação de editais. A plataforma automatiza:

- **Formatação dos critérios de avaliação:** Os critérios são padronizados e formatados de acordo com as melhores práticas.
- **Avaliação dos editais:** Utilizando IA, o IaEditais avalia editais com base nos critérios estabelecidos, proporcionando análises precisas e imparciais.

## Contribuição

Sinta-se à vontade para contribuir com este projeto. Envie pull requests e abra issues conforme necessário.

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
