import { expect, test } from "@playwright/test";

import {
    buildNdviGeoJsonCollection,
    formatNdviVariation,
    getNdviFillColor,
    mapSafraTalhoesParaNdvi,
    type AreaProdutivaGeo,
    type NDVITalhaoResumo,
    type SafraTalhaoApiItem,
} from "./ndvi-view-model";

const POLIGONO_VALIDO: GeoJSON.Polygon = {
    type: "Polygon",
    coordinates: [
        [
            [-55.7, -12.5],
            [-55.69, -12.5],
            [-55.69, -12.51],
            [-55.7, -12.51],
            [-55.7, -12.5],
        ],
    ],
};

test.describe("ndvi-view-model", () => {
    test("mapSafraTalhoesParaNdvi usa area_id em vez de id do vínculo, deduplica e trata nome nulo", () => {
        const items: SafraTalhaoApiItem[] = [
            { id: "vinculo-1", area_id: "area-1", nome: "Talhão 01" },
            { id: "vinculo-2", area_id: "area-1", nome: "Talhão 01 Duplicado" },
            { id: "vinculo-3", area_id: "area-2", nome: null },
        ];

        expect(mapSafraTalhoesParaNdvi(items)).toEqual([
            { id: "area-1", nome: "Talhão 01" },
            { id: "area-2", nome: "Área sem nome" },
        ]);
    });

    test("getNdviFillColor retorna cores padronizadas por faixa de NDVI", () => {
        expect(getNdviFillColor(null)).toBe("#94a3b8");
        expect(getNdviFillColor(undefined)).toBe("#94a3b8");
        expect(getNdviFillColor(-0.05)).toBe("#ef4444");
        expect(getNdviFillColor(0.15)).toBe("#ef4444");
        expect(getNdviFillColor(0.2)).toBe("#f59e0b");
        expect(getNdviFillColor(0.399)).toBe("#f59e0b");
        expect(getNdviFillColor(0.4)).toBe("#22c55e");
        expect(getNdviFillColor(0.599)).toBe("#22c55e");
        expect(getNdviFillColor(0.6)).toBe("#059669");
        expect(getNdviFillColor(0.88)).toBe("#059669");
    });

    test("formatNdviVariation formata sinais positivo, negativo, zero e nulo", () => {
        expect(formatNdviVariation(4.2)).toBe("+4.2%");
        expect(formatNdviVariation(-12)).toBe("-12.0%");
        expect(formatNdviVariation(0)).toBe("0.0%");
        expect(formatNdviVariation(null)).toBe("—");
        expect(formatNdviVariation(undefined)).toBe("—");
    });

    test("buildNdviGeoJsonCollection filtra geometrias inválidas e injeta propriedades reais", () => {
        const empty = buildNdviGeoJsonCollection([], new Map(), null);
        expect(empty).toEqual({ type: "FeatureCollection", features: [] });

        const areas: AreaProdutivaGeo[] = [
            {
                id: "area-1",
                nome: "Talhão Alfa",
                tipo: "TALHAO",
                geometria: POLIGONO_VALIDO,
            },
            {
                id: "area-2",
                nome: "Talhão Beta",
                tipo: "TALHAO",
                geometria: {
                    type: "Feature",
                    properties: {},
                    geometry: POLIGONO_VALIDO,
                },
            },
            {
                id: "area-3",
                nome: "Talhão Sem Polígono",
                tipo: "TALHAO",
                geometria: null,
            },
            {
                id: "area-4",
                nome: "Ponto Ignorado",
                tipo: "PIQUETE",
                geometria: { type: "Point", coordinates: [-55.7, -12.5] },
            },
        ];

        const resumoMap = new Map<string, NDVITalhaoResumo>([
            [
                "area-1",
                {
                    talhao_id: "area-1",
                    talhao_nome: "Talhão Alfa",
                    tipo_area: "TALHAO",
                    area_hectares: 100,
                    unidade_produtiva_id: "up-1",
                    total_imagens: 2,
                    indice_atual: 0.78,
                    indice_anterior: 0.72,
                    variacao_pct: 8.3,
                    cobertura_nuvens_pct: 5,
                    ultima_captura: "2026-11-18",
                    tendencia: "SUBINDO",
                    classificacao: "Excelente",
                    satelite: "QGIS",
                },
            ],
        ]);

        const fc = buildNdviGeoJsonCollection(areas, resumoMap, "area-1");
        expect(fc.type).toBe("FeatureCollection");
        expect(fc.features).toHaveLength(2);

        expect(fc.features[0].properties).toEqual({
            id: "area-1",
            nome: "Talhão Alfa",
            ndvi_color: "#059669",
            indice_atual: 0.78,
            classificacao: "Excelente",
            selected: true,
        });

        expect(fc.features[1].properties).toEqual({
            id: "area-2",
            nome: "Talhão Beta",
            ndvi_color: "#94a3b8",
            indice_atual: null,
            classificacao: "Sem dados",
            selected: false,
        });
    });
});
