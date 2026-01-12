from app.models import db, Produto

def criar_produtos_exemplo():
    produtos_exemplo = [
        {"nome": "Alumínio Puro", "descricao": "Alumínio de alta pureza"},
        {"nome": "Alumínio Liga 6061", "descricao": "Liga estrutural 6061"},
        {"nome": "Alumínio Liga 7075", "descricao": "Liga aeronáutica 7075"},
        {"nome": "Cobre Eletrolítico", "descricao": "Cobre para uso elétrico"},
        {"nome": "Bronze", "descricao": "Liga de cobre e estanho"},
        {"nome": "Latão", "descricao": "Liga de cobre e zinco"},
        {"nome": "Aço Carbono", "descricao": "Aço de baixo carbono"},
        {"nome": "Aço Inoxidável 304", "descricao": "Inox austenítico 304"},
        {"nome": "Aço Inoxidável 316", "descricao": "Inox com molibdênio"},
        {"nome": "Titânio Grade 2", "descricao": "Titânio comercialmente puro"},
        {"nome": "Níquel", "descricao": "Níquel puro"},
        {"nome": "Zinco", "descricao": "Zinco para galvanização"},
        {"nome": "Estanho", "descricao": "Estanho puro"},
        {"nome": "Chumbo", "descricao": "Chumbo reciclado"},
        {"nome": "PET Cristal", "descricao": "Polietileno tereftalato cristal"},
        {"nome": "PET Verde", "descricao": "Polietileno tereftalato colorido"},
        {"nome": "PEAD", "descricao": "Polietileno de alta densidade"},
        {"nome": "PEBD", "descricao": "Polietileno de baixa densidade"},
        {"nome": "PP", "descricao": "Polipropileno"},
        {"nome": "PVC Rígido", "descricao": "Policloreto de vinila rígido"},
        {"nome": "PVC Flexível", "descricao": "Policloreto de vinila flexível"},
        {"nome": "PS", "descricao": "Poliestireno"},
        {"nome": "ABS", "descricao": "Acrilonitrila butadieno estireno"},
        {"nome": "Nylon", "descricao": "Poliamida"},
        {"nome": "Papel Branco", "descricao": "Papel branco limpo"},
        {"nome": "Papelão", "descricao": "Papelão ondulado"},
        {"nome": "Papel Misto", "descricao": "Papel de diversas cores"},
        {"nome": "Vidro Transparente", "descricao": "Vidro incolor"},
        {"nome": "Vidro Âmbar", "descricao": "Vidro âmbar"},
        {"nome": "Vidro Verde", "descricao": "Vidro verde"},
    ]
    
    count = 0
    for p_data in produtos_exemplo:
        existing = Produto.query.filter_by(nome=p_data["nome"]).first()
        if not existing:
            produto = Produto(
                nome=p_data["nome"],
                descricao=p_data["descricao"],
                ativo=True
            )
            db.session.add(produto)
            count += 1
    
    if count > 0:
        db.session.commit()
        print(f" {count} produtos de exemplo criados automaticamente!")
