// Página de Diagnóstico IA - Upload e Análise de Imagens.

'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload, Camera, CheckCircle, AlertCircle, Loader2, Lock } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import Link from 'next/link'
import { useHasTier } from '@/hooks/use-has-tier'
import { getApiBaseUrl } from '@/lib/runtime-config'

interface Diagnostico {
  id: number
  praga_doenca: {
    id: number
    nome: string
    nome_cientifico: string
    tipo: string
    descricao: string
    sintomas: string
  } | null
  confianca: number
  status: string
  created_at: string
  recomendacoes: Array<{
    id: number
    tratamento: {
      id: number
      nome_comercial: string
      principio_ativo: string
      dosagem: string
    } | null
    prioridade: number
  }>
}

export default function IADiagnosticoPage() {
  const [uploading, setUploading] = useState(false)
  const [diagnostico, setDiagnostico] = useState<Diagnostico | null>(null)
  const [imagemPreview, setImagemPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasProfessionalTier = useHasTier("PROFISSIONAL")

  if (!hasProfessionalTier) {
    return (
      <div className="container mx-auto p-6">
        <Alert className="rounded-sm">
          <Lock className="size-4" />
          <AlertTitle>Diagnóstico IA disponível no PROFISSIONAL</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>O plano atual mantém a operação agrícola básica. Upload e análise automática de imagens exigem tier PROFISSIONAL.</p>
            <Button asChild size="sm" className="rounded-sm">
              <Link href="/dashboard/settings/billing">Ver planos</Link>
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const handleUpload = async (file: File) => {
    setUploading(true)
    setError(null)
    setDiagnostico(null)

    // Criar preview
    const reader = new FileReader()
    reader.onload = (e) => setImagemPreview(e.target?.result as string)
    reader.readAsDataURL(file)

    // Upload para API
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${getApiBaseUrl()}/ia-diagnostico/diagnosticar`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Falha ao processar imagem')
      }

      const data = await response.json()
      setDiagnostico(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao processar diagnóstico')
    } finally {
      setUploading(false)
    }
  }

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleUpload(file)
    }
  }

  const getTipoBadgeColor = (tipo: string) => {
    switch (tipo) {
      case 'praga': return 'bg-red-500'
      case 'doenca': return 'bg-orange-500'
      case 'nutricional': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  const getConfiancaColor = (confianca: number) => {
    if (confianca >= 0.85) return 'text-green-600'
    if (confianca >= 0.70) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Camera className="w-8 h-8 text-green-600" />
        <div>
          <h1 className="text-3xl font-bold">Diagnóstico IA de Pragas e Doenças</h1>
          <p className="text-muted-foreground">
            Envie uma imagem da folha ou planta para diagnóstico automático
          </p>
        </div>
      </div>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Upload de Imagem</CardTitle>
          <CardDescription>
            Selecione uma imagem clara da folha ou planta afetada
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <label
              htmlFor="image-upload"
              className={`flex flex-col items-center justify-center w-64 h-48 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                uploading ? 'border-gray-300 bg-gray-50' : 'border-green-300 hover:bg-green-50'
              }`}
            >
              {imagemPreview ? (
                <img src={imagemPreview} alt="Preview" className="w-full h-full object-cover rounded-lg" />
              ) : (
                <>
                  <Upload className="w-12 h-12 text-gray-400 mb-2" />
                  <span className="text-sm text-gray-500">
                    {uploading ? 'Processando...' : 'Clique para upload'}
                  </span>
                </>
              )}
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                onChange={onFileSelect}
                disabled={uploading}
                className="hidden"
              />
            </label>

            {uploading && (
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-green-600" />
                  <span className="text-sm font-medium">Analisando imagem com IA...</span>
                </div>
                <Progress value={60} className="w-full" />
                <p className="text-xs text-muted-foreground">
                  Nossa IA está identificando possíveis pragas ou doenças
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Result Section */}
      {diagnostico && diagnostico.praga_doenca && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {diagnostico.praga_doenca.nome}
                    <Badge className={getTipoBadgeColor(diagnostico.praga_doenca.tipo)}>
                      {diagnostico.praga_doenca.tipo}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="italic">
                    {diagnostico.praga_doenca.nome_cientifico}
                  </CardDescription>
                </div>
                <div className={`text-2xl font-bold ${getConfiancaColor(diagnostico.confianca)}`}>
                  {(diagnostico.confianca * 100).toFixed(1)}% confiança
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">Descrição</h4>
                <p className="text-sm text-muted-foreground">
                  {diagnostico.praga_doenca.descricao}
                </p>
              </div>

              <div>
                <h4 className="font-semibold mb-2">Sintomas Identificados</h4>
                <ul className="text-sm text-muted-foreground list-disc list-inside">
                  {JSON.parse(diagnostico.praga_doenca.sintomas || '[]').map((sintoma: string, i: number) => (
                    <li key={i}>{sintoma}</li>
                  ))}
                </ul>
              </div>

              {diagnostico.status === 'pendente' && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Este diagnóstico foi gerado automaticamente pela IA. Confirme com um agrônomo para maior precisão.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Tratamentos Recomendados */}
          {diagnostico.recomendacoes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  Tratamentos Recomendados
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {diagnostico.recomendacoes
                    .sort((a, b) => a.prioridade - b.prioridade)
                    .map((rec) => (
                      <div
                        key={rec.id}
                        className="p-4 border rounded-lg bg-gray-50"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={rec.prioridade === 1 ? 'default' : 'secondary'}>
                            Prioridade {rec.prioridade}
                          </Badge>
                          {rec.tratamento && (
                            <span className="font-semibold">{rec.tratamento.nome_comercial}</span>
                          )}
                        </div>
                        {rec.tratamento && (
                          <div className="text-sm space-y-1">
                            <p><strong>Princípio Ativo:</strong> {rec.tratamento.principio_ativo}</p>
                            <p><strong>Dosagem:</strong> {rec.tratamento.dosagem}</p>
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Histórico Recente */}
      <HistoricoRecente />
    </div>
  )
}

function HistoricoRecente() {
  const [historico, setHistorico] = useState<Diagnostico[]>([])

  useEffect(() => {
    fetch(`${getApiBaseUrl()}/ia-diagnostico/diagnosticos?limit=5`, {
      credentials: 'include',
    })
      .then((res) => res.json())
      .then((data) => setHistorico(data))
      .catch(console.error)
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Histórico Recente</CardTitle>
      </CardHeader>
      <CardContent>
        {historico.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum diagnóstico recente</p>
        ) : (
          <div className="space-y-2">
            {historico.map((diag) => (
              <div key={diag.id} className="flex items-center justify-between p-3 border rounded">
                <div>
                  <p className="font-medium">
                    {diag.praga_doenca?.nome || 'Diagnóstico pendente'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(diag.created_at).toLocaleDateString('pt-BR')}
                  </p>
                </div>
                <Badge variant={diag.status === 'confirmado' ? 'default' : 'secondary'}>
                  {diag.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
