/**
 * Geocodificação — converte endereço brasileiro em coordenadas.
 * Cadeia de fallback: CEP → Município/UF → Centro do Brasil
 *
 * Usa Nominatim (OpenStreetMap) — gratuito, sem token, rate limit 1 req/s.
 */

export interface GeoResult {
  lat: number;
  lng: number;
  source: "cep" | "cidade" | "fallback";
  display_name?: string;
}

const CENTRO_BRASIL = { lat: -14.235, lng: -51.9253 };

/**
 * Busca coordenadas pelo CEP usando Nominatim.
 * Formato CEP: "01310-100" ou "01310100"
 */
export async function geocodeCep(cep: string): Promise<GeoResult | null> {
  const cepLimpo = cep.replace(/\D/g, "");
  if (cepLimpo.length !== 8) return null;

  try {
    const resp = await fetch(
      `https://nominatim.openstreetmap.org/search?postalcode=${cepLimpo}&country=br&format=json&limit=1`,
      { headers: { "Accept-Language": "pt-BR" } }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        source: "cep",
        display_name: data[0].display_name,
      };
    }
  } catch {
    /* silencioso — fallback para próxima tentativa */
  }
  return null;
}

/**
 * Busca coordenadas pelo município + UF usando Nominatim.
 */
export async function geocodeCidade(municipio: string, uf: string): Promise<GeoResult | null> {
  if (!municipio || !uf) return null;

  try {
    const query = encodeURIComponent(`${municipio}, ${uf}, Brazil`);
    const resp = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${query}&format=json&limit=1&country=br`,
      { headers: { "Accept-Language": "pt-BR" } }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        source: "cidade",
        display_name: data[0].display_name,
      };
    }
  } catch {
    /* silencioso */
  }
  return null;
}

/**
 * Resolve o melhor centro de mapa para uma fazenda.
 * Tenta na ordem: coordenadas_sede → CEP → município/UF → centro do Brasil.
 */
export async function resolverCentroFazenda(fazenda: {
  coordenadas_sede?: string | null;
  cep?: string | null;
  municipio?: string | null;
  uf?: string | null;
}): Promise<{ longitude: number; latitude: number; zoom: number; source: string }> {
  // 1. Coordenadas exatas da sede
  if (fazenda.coordenadas_sede) {
    const parts = fazenda.coordenadas_sede.split(",");
    if (parts.length === 2) {
      const lat = parseFloat(parts[0].trim());
      const lng = parseFloat(parts[1].trim());
      if (!isNaN(lat) && !isNaN(lng)) {
        return { longitude: lng, latitude: lat, zoom: 13, source: "coordenadas" };
      }
    }
  }

  // 2. Geocodificar pelo CEP
  if (fazenda.cep) {
    const result = await geocodeCep(fazenda.cep);
    if (result) {
      return { longitude: result.lng, latitude: result.lat, zoom: 13, source: result.source };
    }
  }

  // 3. Geocodificar por município/UF
  if (fazenda.municipio && fazenda.uf) {
    const result = await geocodeCidade(fazenda.municipio, fazenda.uf);
    if (result) {
      return { longitude: result.lng, latitude: result.lat, zoom: 10, source: result.source };
    }
  }

  // 4. Fallback
  return {
    longitude: CENTRO_BRASIL.lng,
    latitude: CENTRO_BRASIL.lat,
    zoom: 4,
    source: "fallback",
  };
}
