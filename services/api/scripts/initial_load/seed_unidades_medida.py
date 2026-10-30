"""Unidades globais aprovadas para a carga inicial."""

# Códigos conforme ISO 80000 quando aplicável. A unidade de dia usa `d`.
UNITS = (
    ("KG", "Quilograma", "massa", "KG", "1", 2, True),
    ("G", "Grama", "massa", "KG", "0.001", 3, False),
    ("TON", "Tonelada", "massa", "KG", "1000", 4, False),
    ("SC60", "Saca 60 kg", "massa", "KG", "60", 2, False),
    ("SC50", "Saca 50 kg", "massa", "KG", "50", 2, False),
    ("L", "Litro", "volume", "L", "1", 2, True),
    ("ML", "Mililitro", "volume", "L", "0.001", 3, False),
    ("M3", "Metro cúbico", "volume", "L", "1000", 4, False),
    ("HA", "Hectare", "area", "HA", "1", 2, True),
    ("M2", "Metro quadrado", "area", "HA", "0.0001", 0, False),
    ("HM", "Hora-máquina", "hora_maquina", "HM", "1", 2, True),
    ("HH", "Homem-hora", "hora_homem", "HH", "1", 2, True),
    ("UN", "Unidade", "contagem", "UN", "1", 0, True),
    ("BRL", "Real brasileiro", "moeda", "BRL", "1", 2, True),
    ("h", "Hora", "tempo", "h", "1", 2, True),
    ("d", "Dia", "tempo", "h", "24", 2, False),
    ("min", "Minuto", "tempo", "h", "0.016666667", 4, False),
    ("s", "Segundo", "tempo", "h", "0.000277778", 0, False),
    ("SEMANA", "Semana", "tempo", "h", "168", 0, False),
    ("MES", "Mês", "tempo", "h", "720", 0, False),
    ("a", "Ano", "tempo", "h", "8760", 0, False),
    ("MANHA", "Manhã (turno de 8h)", "tempo", "h", "8", 0, False),
    ("TARDE", "Tarde (turno de 8h)", "tempo", "h", "8", 0, False),
    ("NOITE", "Noite (turno de 8h)", "tempo", "h", "8", 0, False),
)
