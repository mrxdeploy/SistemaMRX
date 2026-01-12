-- Adiciona campo de justificativa da IA ao modelo ItemSolicitacao
ALTER TABLE itens_solicitacao 
ADD COLUMN IF NOT EXISTS justificativa_ia TEXT;

-- Comentário explicativo
COMMENT ON COLUMN itens_solicitacao.justificativa_ia IS 'Justificativa fornecida pela IA Gemini para a classificação sugerida';
