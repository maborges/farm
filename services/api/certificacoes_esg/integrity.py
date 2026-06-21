import hashlib
import json
from typing import Any

def canonical_json(payload: dict[str, Any]) -> str:
    """
    Serializa um dicionário Python em uma representação JSON canônica e determinística.
    
    Regras:
    - Chaves são ordenadas alfabeticamente.
    - Nenhum espaço em branco supérfluo (separadores ',' e ':').
    - Codificação segura de caracteres não-ASCII (ensure_ascii=False) para manter o UTF-8 intacto se for usado em bytes.
    """
    # Se o payload for None, retorna uma string json vazia correspondente
    if payload is None:
        return "{}"
        
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':')
    )

def calculate_snapshot_hash(snapshot_json: dict[str, Any]) -> str:
    """
    Calcula o hash SHA-256 de um snapshot em formato JSON canônico.
    
    Retorna o hash hexadecimal.
    """
    canonical_str = canonical_json(snapshot_json)
    # Codifica a string para UTF-8 antes de gerar o hash
    hash_object = hashlib.sha256(canonical_str.encode('utf-8'))
    return hash_object.hexdigest()

def verify_snapshot_hash(snapshot_json: dict[str, Any], snapshot_hash: str) -> bool:
    """
    Verifica se o hash fornecido corresponde ao conteúdo do snapshot.
    
    Retorna True se for VÁLIDO (idêntico), False se for INVÁLIDO.
    """
    if not snapshot_hash:
        return False
        
    calculated_hash = calculate_snapshot_hash(snapshot_json)
    # Comparação segura (time-safe) é recomendada para hashes, mas hexdigest == hexdigest é aceitável para verificação pública
    import hmac
    return hmac.compare_digest(calculated_hash, snapshot_hash)
