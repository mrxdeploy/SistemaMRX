
```python
#!/usr/bin/env python3
"""
Script para verificar estrutura de lotes e sublotes no Railway
"""

from app import create_app
from app.models import db, Lote

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE LOTES E SUBLOTES")
    print("="*60)
    
    # Buscar lotes principais
    lotes_principais = Lote.query.filter(
        Lote.lote_pai_id.is_(None)
    ).order_by(Lote.data_criacao.desc()).limit(10).all()
    
    print(f"\n📦 Total de lotes principais: {len(lotes_principais)}\n")
    
    for lote in lotes_principais:
        print(f"{'='*60}")
        print(f"🏷️  Lote: {lote.numero_lote}")
        print(f"   ID: {lote.id}")
        print(f"   Status: {lote.status}")
        print(f"   Peso Total: {lote.peso_total_kg} kg")
        print(f"   Peso Líquido: {lote.peso_liquido} kg" if lote.peso_liquido else "   Peso Líquido: N/A")
        print(f"   Fornecedor: {lote.fornecedor.nome if lote.fornecedor else 'N/A'}")
        print(f"   Tipo: {lote.tipo_lote.nome if lote.tipo_lote else 'N/A'}")
        print(f"   Data: {lote.data_criacao}")
        
        # Verificar sublotes
        sublotes = Lote.query.filter_by(lote_pai_id=lote.id).all()
        
        if sublotes:
            print(f"\n   🔹 SUBLOTES ({len(sublotes)}):")
            peso_total_sublotes = 0
            for i, sublote in enumerate(sublotes, 1):
                peso = sublote.peso_liquido if sublote.peso_liquido else sublote.peso_total_kg
                peso_total_sublotes += peso if peso else 0
                print(f"      {i}. {sublote.numero_lote}")
                print(f"         • Tipo: {sublote.tipo_lote.nome if sublote.tipo_lote else 'N/A'}")
                print(f"         • Peso: {peso} kg")
                print(f"         • Status: {sublote.status}")
            
            print(f"\n   📊 Total separado: {peso_total_sublotes:.2f} kg")
        else:
            print(f"\n   ⚠️  Nenhum sublote encontrado (lote não foi separado)")
        
        print(f"{'='*60}\n")
    
    # Estatísticas gerais
    print("\n" + "="*60)
    print("📊 ESTATÍSTICAS GERAIS")
    print("="*60)
    
    total_lotes = Lote.query.count()
    total_principais = Lote.query.filter(Lote.lote_pai_id.is_(None)).count()
    total_sublotes = Lote.query.filter(Lote.lote_pai_id.isnot(None)).count()
    
    print(f"Total de lotes no sistema: {total_lotes}")
    print(f"Lotes principais: {total_principais}")
    print(f"Sublotes: {total_sublotes}")
    print(f"\n{'='*60}\n")
```
