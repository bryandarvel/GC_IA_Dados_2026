# Aula 14 · API da Casa de Sucos

API em Python e FastAPI para consultar frutas, cadastrar receitas de sucos e recalcular seus valores nutricionais. Os dados de cada fruta vêm da [Fruityvice](https://www.fruityvice.com/).

Informe os nomes das frutas em inglês, como `banana`, `strawberry` e `apple`. Cada item na lista representa 100 g da fruta. Os totais são a soma das calorias (kcal) e do açúcar (g) de cada item. Se uma fruta aparecer duas vezes, ela contará como 200 g. Os sucos ficam em memória enquanto a aplicação está em execução.

## Como executar

É necessário ter Python 3.10 ou superior e conexão com a internet para consultar a Fruityvice. A partir da raiz do repositório:

```bash
cd aula_14
python -m venv .venv
```

Ative o ambiente virtual no terminal que estiver usando.

```bash
# Linux, macOS ou WSL
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências e inicie o servidor.

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Abra o [Swagger](http://127.0.0.1:8000/docs).

## Rotas

| Método e caminho | O que a rota faz | Resposta de sucesso |
| --- | --- | --- |
| `GET /frutas/{nome}` | Consulta o nome, as calorias e o açúcar de uma fruta | `200 OK` |
| `POST /sucos` | Cadastra um suco e retorna seu ID e seus totais | `201 Created` |
| `GET /sucos` | Lista os sucos cadastrados, incluindo os totais | `200 OK` |
| `PUT /sucos/{id}` | Substitui a lista de frutas e recalcula os totais | `200 OK` |

A consulta de fruta retorna os campos `nome`, `calorias` e `acucar`. O texto do nome vem da Fruityvice. O `PUT` recebe apenas a nova lista de frutas e conserva o nome, a descrição do gosto e o ID da receita.

## Exemplos para testar no Swagger

Em cada rota, clique em **Try it out**, informe os parâmetros ou cole o JSON e clique em **Execute**.

1. Em `GET /sucos`, confira que um servidor recém-iniciado retorna `[]`.
2. Em `GET /frutas/{nome}`, consulte `banana` e `strawberry`. Confira o status `200` e anote as calorias e o açúcar informados em cada consulta.
3. Em `POST /sucos`, envie o JSON abaixo. Confira o status `201` e compare os totais com a soma das duas consultas anteriores. Anote o ID retornado.

```json
{
  "nome": "Vitamina Tropical",
  "frutas": ["banana", "strawberry"],
  "tem_gosto_de": "Tamarindo"
}
```

4. Execute `GET /sucos` novamente e confira se a receita foi cadastrada com os totais que o `POST` retornou.
5. No `PUT /sucos/{id}`, informe o ID do cadastro e envie o JSON abaixo. Confira o status `200` e veja se os totais correspondem a duas porções de banana. Use `GET /sucos` para confirmar a atualização.

```json
{
  "frutas": ["banana", "banana"]
}
```

6. Em `GET /frutas/{nome}`, consulte `fruta-inexistente`. A resposta esperada é `404`, com a mensagem abaixo. Envie também essa fruta em uma lista no `PUT` e confira pela listagem que a receita continua como antes.

```json
{
  "detail": "Não encontramos a fruta 'fruta-inexistente'. Use um nome em inglês, como banana."
}
```

O `PUT` também retorna `404` se o ID do suco não existir. Uma lista vazia ou um campo obrigatório em branco gera `422`. Se a Fruityvice falhar ou exceder o tempo de resposta, a API retorna `502` ou `504`, respectivamente.

## Verificação executada

A aplicação foi verificada com respostas simuladas da Fruityvice. A verificação
cobriu a página `/docs`, o esquema OpenAPI, as quatro rotas, o cálculo dos totais,
o recálculo no `PUT` e as respostas `404`, `422`, `502` e `504`. Também
foi confirmado que uma consulta malsucedida preserva os sucos já cadastrados.

A tentativa de consultar a Fruityvice diretamente excedeu o tempo de conexão
neste ambiente. Para verificar a integração com o serviço real, execute os
exemplos acima no Swagger com acesso à internet.
