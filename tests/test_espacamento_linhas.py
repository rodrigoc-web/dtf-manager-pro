"""
Cobre o espaçamento entre linhas configurável (gap_linhas) -- mesma ideia
de tests/test_espacamento_colunas.py, mas pro respiro VERTICAL entre
linhas da grade, pedido pelo usuário depois de ver espaço demais entre
uma linha e outra na folha gerada.
"""
from PIL import Image
from services.export_service import montar_folha_grade, montar_folha_combinada


def _img(w, h):
    return Image.new("RGBA", (w, h), (255, 0, 0, 255))


def _artes(n, w=100, h=100):
    return [(None, _img(w, h)) for _ in range(n)]


def test_gap_linhas_padrao_usa_o_mesmo_valor_de_gap():
    """Sem passar gap_linhas, comportamento antigo é preservado -- quem não
    tocar na configuração nova não deve ver nenhuma diferença."""
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0, gap=10)
    assert folha.height == 2 * 200 + 10


def test_gap_linhas_diferente_de_gap_coluna():
    """Espaçamento entre linhas menor que o espaçamento entre colunas --
    exatamente o pedido: menos respiro vertical, sem mexer no horizontal."""
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_colunas=80, gap_linhas=5)
    # largura: 2 colunas de 200 + 1 gap de 80 (o de COLUNA, não mudou) = 480
    assert folha.width == max(2000, 480)
    # altura: 2 linhas de 200 + 1 gap de 5 = 405
    assert folha.height == 405


def test_gap_linhas_zero_encosta_as_linhas():
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_linhas=0)
    assert folha.height == 400   # 200+200, sem gap nenhum


def test_gap_linhas_negativo_vira_zero():
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0,
                               gap=10, gap_linhas=-50)
    assert folha.height == 400


def test_posicao_y_da_segunda_linha_respeita_gap_linhas():
    """Confere a posição Y de verdade da 2ª linha (não só a altura da
    folha) -- é o que realmente separa uma arte da outra na impressão."""
    artes = [(None, _img(150, 150)) for _ in range(4)]   # 2x2, mesmo tamanho da célula
    folha = montar_folha_grade(artes, num_colunas=2, largura_coluna=150,
                               altura_coluna=150, largura_rolo=1000, margem_lateral=0,
                               gap=5, gap_linhas=60)

    import numpy as np
    arr = np.array(folha)
    coluna_meio = arr[:, 75, 3]   # canal alpha na largura do meio da arte
    opacos = np.where(coluna_meio > 0)[0]
    # 1a linha: y de 0 a 149; 2a linha: y de 150+60=210 a 359
    inicio_2a_linha = opacos[opacos >= 150].min()
    assert inicio_2a_linha == 210, f"esperava a 2a linha comecar em y=210, comecou em {inicio_2a_linha}"


def test_montar_folha_combinada_repassa_gap_linhas():
    """montar_folha_combinada precisa passar gap_linhas adiante pras duas
    chamadas internas de montar_folha_grade (Time e Profissao)."""
    folha = montar_folha_combinada(
        artes_profissao=_artes(4), artes_time=[],
        num_colunas=2, largura_coluna=200, altura_coluna=200, largura_rolo=2000,
        gap_linhas=100)
    assert folha.height == 2 * 200 + 100
