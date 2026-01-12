-- Migration: Add tabela_preco_status columns to fornecedores table
-- Date: 2025-11-29
-- Description: Adds workflow fields for price table approval status

-- Add status column (pendente_aprovacao, aprovada, pendente_reenvio)
ALTER TABLE fornecedores 
ADD COLUMN IF NOT EXISTS tabela_preco_status VARCHAR(50) DEFAULT 'pendente_aprovacao';

-- Add approval timestamp
ALTER TABLE fornecedores 
ADD COLUMN IF NOT EXISTS tabela_preco_aprovada_em TIMESTAMP;

-- Add approver foreign key
ALTER TABLE fornecedores 
ADD COLUMN IF NOT EXISTS tabela_preco_aprovada_por_id INTEGER REFERENCES usuarios(id);

-- Create index for status filtering
CREATE INDEX IF NOT EXISTS idx_fornecedor_tabela_preco_status 
ON fornecedores(tabela_preco_status);

-- Comment on columns
COMMENT ON COLUMN fornecedores.tabela_preco_status IS 'Status da tabela de preços: pendente_aprovacao, aprovada, pendente_reenvio';
COMMENT ON COLUMN fornecedores.tabela_preco_aprovada_em IS 'Data/hora da aprovação da tabela de preços';
COMMENT ON COLUMN fornecedores.tabela_preco_aprovada_por_id IS 'ID do administrador que aprovou a tabela';
