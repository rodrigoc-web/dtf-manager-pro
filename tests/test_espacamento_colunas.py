"""
Cobre o espaçamento entre colunas configurável (gap_colunas), pedido pelo
usuário depois de ver as artes saindo praticamente grudadas na mesma
folha -- separado do espaçamento entre LINHAS (gap), que continua fixo.
"""
from PIL import Image
from services.export_service import montar_folha_grade, montar_folha_combinada


def _img(w, h):
    return Image.new("RGBA", (w, h), (255, 0, 0, 255))


def _artes(n, w=100, h=100):
    return [(None, _img(w, h)) for _ in range(n)]


def test_gap_colunas_padrao_usa_o_mesmo_valor_de_gap():
    """Sem passar gap_colunas, comportamento antigo é preservado (mesmo
    espaçamento pra linha e coluna) -- quem não tocar na configuração
    nova não deve ver nenhuma diferença."""
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0, gap=10)
    assert folha.width == max(2000, 2 * 200 + 10)


def test_gap_colunas_diferente_de_gap_linha():
    """Espaçamento entre colunas maior que o espaçamento entre linhas --
    exatamente o pedido: mais respiro na horizontal, sem mexer no vertical."""
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_colunas=80)
    # largura: 2 colunas de 200 + 1 gap de 80 = 480
    assert folha.width == max(2000, 480)
    # altura: 2 linhas de 200 + 1 gap de 10 (o de LINHA, nao mudou) = 410
    assert folha.height == 410


def test_gap_colunas_zero_encosta_as_colunas():
    """0 = colunas encostadas (comportamento que o usuario reclamou que
    ja acontecia sem a opcao existir) -- continua permitido de proposito."""
    folha = montar_folha_grade(_artes(2), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_colunas=0)
    assert folha.width == max(2000, 400)   # 200+200, sem gap nenhum


def test_gap_colunas_negativo_vira_zero():
    folha = montar_folha_grade(_artes(2), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_colunas=-50)
    assert folha.width == max(2000, 400)


def test_posicao_x_da_segunda_coluna_respeita_gap_colunas():
    """Confere a posicao X de verdade da 2a coluna (nao so a largura da
    folha) -- e o que realmente separa uma arte da outra na impressao."""
    artes = [(None, _img(150, 150)) for _ in range(2)]   # mesmo tamanho da celula, sem letterbox
    folha = montar_folha_grade(artes, num_colunas=2, largura_coluna=150,
                               altura_coluna=150, largura_rolo=1000, margem_lateral=0,
                               gap=5, gap_colunas=60)

    import numpy as np
    arr = np.array(folha)
    linha_meio = arr[75, :, 3]   # canal alpha na altura do meio da arte
    opacos = np.where(linha_meio > 0)[0]
    # 1a arte: x de 0 a 149; 2a arte: x de 150+60=210 a 359
    inicio_2a_arte = opacos[opacos >= 150].min()
    assert inicio_2a_arte == 210, f"esperava a 2a coluna comecar em x=210, comecou em {inicio_2a_arte}"


def test_montar_folha_combinada_repassa_gap_colunas():
    """montar_folha_combinada precisa passar gap_colunas adiante pras duas
    chamadas internas de montar_folha_grade (Time e Profissao)."""
    folha = montar_folha_combinada(
        artes_profissao=_artes(2), artes_time=[],
        num_colunas=2, largura_coluna=200, altura_coluna=200, largura_rolo=2000,
        gap_colunas=100)
    assert folha.width == max(2000, 2 * 200 + 100)
