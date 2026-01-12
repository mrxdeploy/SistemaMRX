-- Adicionar coluna material_id ao ItemSolicitacao
ALTER TABLE itens_solicitacao 
ADD COLUMN IF NOT EXISTS material_id INTEGER,
ADD CONSTRAINT fk_itens_solicitacao_material 
  FOREIGN KEY (material_id) REFERENCES materiais_base(id) ON DELETE SET NULL;

-- Tornar tipo_lote_id nullable para retrocompatibilidade
ALTER TABLE itens_solicitacao 
ALTER COLUMN tipo_lote_id DROP NOT NULL;

-- Criar índice para melhorar performance
CREATE INDEX IF NOT EXISTS idx_itens_solicitacao_material 
ON itens_solicitacao(material_id);

COMMENT ON COLUMN itens_solicitacao.material_id IS 'Novo formato: referência direta ao material (substitui tipo_lote_id + classificacao)';
