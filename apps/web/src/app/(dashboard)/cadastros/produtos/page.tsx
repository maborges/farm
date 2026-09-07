import { apiFetchServer } from "@/lib/api-server";
import { 
    ProdutosClient, 
    Produto, 
    Marca, 
    ModeloProduto, 
    CategoriaProduto 
} from "./ProdutosClient";

export default async function CatalogoProdutosPage() {
    // undefined (não []) quando a busca falha no servidor — um array vazio
    // aqui vira "initialData" confiável no React Query por até 5min (staleTime
    // global), mascarando uma falha transitória (ex: pool de conexão do
    // backend) como "não existe nenhum registro". Deixando undefined, o
    // client-side query roda normalmente no mount e busca de novo.
    let initialProdutos: Produto[] | undefined;
    let initialMarcas: Marca[] | undefined;
    let initialModelos: ModeloProduto[] | undefined;
    let initialCategorias: CategoriaProduto[] | undefined;

    try {
        const [prodRes, marcasRes, modelosRes, catRes] = await Promise.allSettled([
            apiFetchServer<Produto[]>("/cadastros/produtos?incluir_sistema=true&ativo=true"),
            apiFetchServer<Marca[]>("/cadastros/marcas?ativo=true"),
            apiFetchServer<ModeloProduto[]>("/cadastros/modelos-produto?ativo=true"),
            apiFetchServer<CategoriaProduto[]>("/cadastros/categorias-produto?ativo=true"),
        ]);

        if (prodRes.status === "fulfilled") initialProdutos = prodRes.value;
        if (marcasRes.status === "fulfilled") initialMarcas = marcasRes.value;
        if (modelosRes.status === "fulfilled") initialModelos = modelosRes.value;
        if (catRes.status === "fulfilled") initialCategorias = catRes.value;
    } catch (e) {
        // Ignora erros
    }

    return (
        <ProdutosClient 
            initialProdutos={initialProdutos}
            initialMarcas={initialMarcas}
            initialModelos={initialModelos}
            initialCategorias={initialCategorias}
        />
    );
}
