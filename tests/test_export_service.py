from unittest.mock import patch
from PIL import Image
from services.export_service import montar_folha_grade, montar_folha_combinada, _ajustar_para_celula


def _img(w, h, cor=(255, 0, 0, 255)):
    return Image.new("RGBA", (w, h), cor)


def _artes(n, w=100, h=100):
    return [(None, _img(w, h)) for _ in range(n)]


# ── _ajustar_para_celula (contain-fit) ──────────────────────────────────────

def test_contain_fit_encolhe_imagem_larga():
    img = _img(400, 100)   # bem mais larga que alta
    ajustada = _ajustar_para_celula(img, largura_max=200, altura_max=200)
    assert ajustada.width == 200
    assert ajustada.height == 50   # proporção mantida (400x100 -> 200x50)


def test_contain_fit_amplia_imagem_pequena():
    img = _img(50, 50)
    ajustada = _ajustar_para_celula(img, largura_max=200, altura_max=200)
    assert ajustada.width == 200
    assert ajustada.height == 200


def test_contain_fit_respeita_a_dimensao_mais_apertada():
    img = _img(100, 200)   # mais alta que larga
    ajustada = _ajustar_para_celula(img, largura_max=100, altura_max=100)
    # altura bateria 100 (escala 0.5), mas largura só cabe com escala 1.0 -> escala = min(1.0, 0.5) = 0.5
    assert ajustada.width == 50
    assert ajustada.height == 100


# ── montar_folha_grade ───────────────────────────────────────────────────────

def test_grade_dimensoes_2_colunas_4_artes():
    folha = montar_folha_grade(_artes(4), num_colunas=2, largura_coluna=200,
                               altura_coluna=200, largura_rolo=2000, margem_lateral=0, gap=10)
    # 2 colunas: 200+10+200 = 410; 2 linhas: 200+10+200 = 410
    assert folha.width == max(2000, 410)
    assert folha.height == 410


def test_grade_1_coluna():
    folha = montar_folha_grade(_artes(3), num_colunas=1, largura_coluna=100,
                               altura_coluna=100, largura_rolo=500, margem_lateral=0, gap=10)
    assert folha.height == 3 * 100 + 2 * 10   # 3 linhas empilhadas


def test_grade_numero_impar_de_artes_nao_quebra():
    """Última linha incompleta (2 colunas, 5 artes -> 3 linhas, última com 1 só)."""
    folha = montar_folha_grade(_artes(5), num_colunas=2, largura_coluna=100,
                               altura_coluna=100, largura_rolo=1000, margem_lateral=0, gap=0)
    assert folha.height == 3 * 100   # ceil(5/2) = 3 linhas


def test_grade_lista_vazia_retorna_folha_minima():
    folha = montar_folha_grade([], num_colunas=2, largura_coluna=100,
                               altura_coluna=100, largura_rolo=500)
    assert folha.width == 500
    assert folha.height == 1


def test_grade_avisa_quando_nao_cabe_no_rolo():
    with patch("services.export_service.log.aviso") as mock_aviso:
        folha = montar_folha_grade(_artes(2), num_colunas=3, largura_coluna=500,
                                   altura_coluna=100, largura_rolo=800, margem_lateral=0, gap=0)
    assert mock_aviso.called
    assert folha.width > 800   # a folha cresce mesmo assim


def test_grade_nao_avisa_quando_cabe():
    with patch("services.export_service.log.aviso") as mock_aviso:
        montar_folha_grade(_artes(2), num_colunas=2, largura_coluna=100,
                           altura_coluna=100, largura_rolo=1000, margem_lateral=0, gap=0)
    assert not mock_aviso.called


def test_grade_guarda_contra_num_colunas_invalido():
    """num_colunas=0 (ou negativo) nao deve quebrar -- trata como 1."""
    folha = montar_folha_grade(_artes(2), num_colunas=0, largura_coluna=100,
                               altura_coluna=100, largura_rolo=500, margem_lateral=0, gap=0)
    assert folha.height == 200   # 2 artes, 1 coluna -> empilhadas


def test_grade_guarda_contra_largura_altura_invalidas():
    folha = montar_folha_grade(_artes(1, w=50, h=50), num_colunas=1, largura_coluna=-10,
                               altura_coluna=0, largura_rolo=100)
    assert folha.width > 0 and folha.height > 0   # nao lanca excecao


# ── montar_folha_combinada ───────────────────────────────────────────────────

def test_combinada_so_profissao():
    folha = montar_folha_combinada(_artes(2), [], num_colunas=2, largura_coluna=100,
                                   altura_coluna=100, largura_rolo=500)
    assert folha.height == 100   # 2 artes, 2 colunas -> 1 linha


def test_combinada_so_time():
    folha = montar_folha_combinada([], _artes(2), num_colunas=2, largura_coluna=100,
                                   altura_coluna=100, largura_rolo=500)
    assert folha.height == 100


def test_combinada_ambos_empilha_verticalmente():
    folha_prof = montar_folha_combinada(_artes(2), [], num_colunas=2, largura_coluna=100,
                                        altura_coluna=100, largura_rolo=500)
    folha_ambos = montar_folha_combinada(_artes(2), _artes(2), num_colunas=2, largura_coluna=100,
                                         altura_coluna=100, largura_rolo=500)
    assert folha_ambos.height > folha_prof.height   # time empilhado em cima


def test_combinada_nenhum_tipo_retorna_folha_minima():
    folha = montar_folha_combinada([], [], num_colunas=2, largura_coluna=100,
                                   altura_coluna=100, largura_rolo=500)
    assert folha.width == 500
    assert folha.height == 1
