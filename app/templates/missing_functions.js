        let subloteEmEdicaoId = null;

        function abrirModalEdicao(id) {
            console.log('✏️ Abrindo edição para sublote ID:', id);
            
            // Garantir que ID seja numérico para encontrar na lista
            const idNum = parseInt(id);
            const sublote = sublotes.find(s => s.id === idNum);
            
            if (!sublote) {
                console.error('❌ Sublote não encontrado na lista local para ID:', id);
                alert('Erro interno: Sublote não encontrado.');
                return;
            }

            subloteEmEdicaoId = idNum;
            document.getElementById('editPeso').value = sublote.peso_total_kg;
            document.getElementById('editQualidade').value = sublote.qualidade_recebida || 'A';
            document.getElementById('editObservacoes').value = sublote.observacoes || '';
            
            // Garantir que o modal esteja visível no topo
            const modal = document.getElementById('modalEdicaoSublote');
            document.body.appendChild(modal); // Move para body para evitar problemas de z-index
            modal.style.display = 'flex';
        }

        function fecharModalEdicao() {
            document.getElementById('modalEdicaoSublote').style.display = 'none';
            subloteEmEdicaoId = null;
        }

        async function salvarEdicaoSublote() {
            if (!subloteEmEdicaoId) return;

            const peso = parseFloat(document.getElementById('editPeso').value);
            const qualidade = document.getElementById('editQualidade').value;
            const observacoes = document.getElementById('editObservacoes').value;

            try {
                const response = await fetch(`/api/separacao/sublotes/${subloteEmEdicaoId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify({ peso, qualidade, observacoes })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.erro || 'Falha ao atualizar sublote');
                }

                fecharModalEdicao();
                await carregarSeparacao(); 
                alert('Sublote atualizado com sucesso!');

            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao atualizar sublote: ' + error.message);
            }
        }

        async function excluirSublote(id) {
            console.log('🗑️ Excluindo sublote ID:', id);
            if (!confirm('Tem certeza que deseja excluir este sublote?')) return;

            try {
                const response = await fetch(`/api/separacao/sublotes/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.erro || 'Falha ao excluir sublote');
                }

                await carregarSeparacao(); 
                alert('Sublote excluído com sucesso!');

            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao excluir sublote: ' + error.message);
            }
        }
