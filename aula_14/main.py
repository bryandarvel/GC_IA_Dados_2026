from decimal import Decimal
from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field, StringConstraints

app = FastAPI(
    title="API da Casa de Sucos",
    description="Consulte frutas na Fruityvice e cadastre receitas de sucos.",
    version="1.0.0",
)

URL_FRUITYVICE = "https://www.fruityvice.com/api/fruit"
TextoObrigatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrutaNutricional(BaseModel):
    nome: str
    calorias: int = Field(ge=0, description="Quilocalorias (kcal) por 100 g.")
    acucar: float = Field(ge=0, allow_inf_nan=False, description="Açúcar (g) por 100 g.")


class FrutasDoSuco(BaseModel):
    frutas: list[TextoObrigatorio] = Field(
        min_length=1,
        description="Nomes em inglês. Cada item da lista equivale a 100 g.",
        examples=[["banana", "strawberry"]],
    )


class SucoCadastro(FrutasDoSuco):
    nome: TextoObrigatorio = Field(examples=["Vitamina Tropical"])
    tem_gosto_de: TextoObrigatorio = Field(examples=["Tamarindo"])


class Suco(SucoCadastro):
    id: int
    total_calorias: int = Field(description="Total de quilocalorias (kcal) da receita.")
    total_acucar: float = Field(description="Total de açúcar (g) da receita.")


sucos: dict[int, Suco] = {}


async def cliente_fruityvice():
    async with httpx.AsyncClient(timeout=8.0) as cliente:
        yield cliente


ClienteFruityvice = Annotated[httpx.AsyncClient, Depends(cliente_fruityvice)]


async def consultar_fruta(nome: str, cliente: httpx.AsyncClient) -> FrutaNutricional:
    nome = nome.strip().lower()
    erro_fruta = f"Não encontramos a fruta '{nome}'. Use um nome em inglês, como banana."

    # Pontos isolados seriam interpretados como segmentos da URL.
    if nome in {"", ".", ".."}:
        raise HTTPException(status_code=404, detail=erro_fruta)

    try:
        resposta = await cliente.get(f"{URL_FRUITYVICE}/{quote(nome, safe='')}")
        if resposta.status_code == 404:
            raise HTTPException(status_code=404, detail=erro_fruta)

        resposta.raise_for_status()
        dados = resposta.json()
        nutrientes = dados["nutritions"]
        return FrutaNutricional(
            nome=dados["name"],
            calorias=nutrientes["calories"],
            acucar=nutrientes["sugar"],
        )
    except httpx.TimeoutException as erro:
        raise HTTPException(status_code=504, detail="A Fruityvice demorou para responder.") from erro
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter os dados nutricionais da Fruityvice.",
        ) from erro


async def calcular_totais(
    frutas: list[str], cliente: httpx.AsyncClient
) -> tuple[int, float]:
    dados_frutas = []
    for nome in frutas:
        dados_frutas.append(await consultar_fruta(nome, cliente))

    total_calorias = sum(fruta.calorias for fruta in dados_frutas)
    total_acucar = sum(Decimal(str(fruta.acucar)) for fruta in dados_frutas)
    return total_calorias, float(total_acucar)


ERROS_FRUITYVICE = {
    404: {"description": "Fruta não encontrada."},
    502: {"description": "Falha ao consultar a Fruityvice."},
    504: {"description": "Tempo limite excedido ao consultar a Fruityvice."},
}


@app.get("/frutas/{nome}", summary="Consultar uma fruta", responses=ERROS_FRUITYVICE)
async def obter_fruta(
    nome: Annotated[str, Path(description="Nome da fruta em inglês.", examples=["banana"])],
    cliente: ClienteFruityvice,
) -> FrutaNutricional:
    return await consultar_fruta(nome, cliente)


@app.post(
    "/sucos",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar um suco",
    responses=ERROS_FRUITYVICE,
)
async def cadastrar_suco(dados: SucoCadastro, cliente: ClienteFruityvice) -> Suco:
    frutas = [nome.lower() for nome in dados.frutas]
    calorias, acucar = await calcular_totais(frutas, cliente)

    suco = Suco(
        id=len(sucos) + 1,
        nome=dados.nome,
        frutas=frutas,
        tem_gosto_de=dados.tem_gosto_de,
        total_calorias=calorias,
        total_acucar=acucar,
    )
    sucos[suco.id] = suco
    return suco


@app.get("/sucos", summary="Listar sucos cadastrados")
async def listar_sucos() -> list[Suco]:
    return list(sucos.values())


@app.put(
    "/sucos/{id}",
    summary="Atualizar as frutas de um suco",
    responses={**ERROS_FRUITYVICE, 404: {"description": "Suco ou fruta não encontrado."}},
)
async def atualizar_suco(id: int, dados: FrutasDoSuco, cliente: ClienteFruityvice) -> Suco:
    suco = sucos.get(id)
    if suco is None:
        raise HTTPException(status_code=404, detail=f"Não encontramos o suco com ID {id}.")

    frutas = [nome.lower() for nome in dados.frutas]
    calorias, acucar = await calcular_totais(frutas, cliente)
    suco_atualizado = suco.model_copy(
        update={"frutas": frutas, "total_calorias": calorias, "total_acucar": acucar}
    )
    sucos[id] = suco_atualizado
    return suco_atualizado
