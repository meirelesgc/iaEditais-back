# IaEditais - Plataforma de Avaliação de Editais

IaEditais, uma API desenvolvida para avaliar editais utilizando modelos de linguagem de grande porte (Large Language Models - LLMs). A plataforma automatiza tanto a formatação dos critérios de avaliação quanto a avaliação dos próprios editais.

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

1. Execute a tarefa principal do projeto:

    ```sh
    task run
    ```

2. Acesse a documentação da API no navegador:
    [http://localhost:8000/redocs](http://localhost:8000/redocs)

## Executando o Projeto com Docker

Você também pode executar o projeto usando Docker. Siga os passos abaixo para construir e iniciar o contêiner Docker:

1. Construa a imagem Docker:

    ```sh
    docker build -t iaeditais .
    ```

2. Inicie o contêiner Docker:

    ```sh
    docker run -p 8000:8000 iaeditais
    ```

3. Acesse a documentação da API no navegador:
    [http://localhost:8000/redocs](http://localhost:8000/redocs)

## Contribuição

Sinta-se à vontade para contribuir com este projeto. Envie pull requests e abra issues conforme necessário.
