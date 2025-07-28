#!/usr/bin/env python3
import csv
import os
import faiss
import numpy as np
import pickle
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def create_medical_knowledge():
    """Cria conhecimento médico direto e funcional"""
    
    print("🏥 Criando conhecimento médico...")
    
    # Conhecimento base essencial
    base_knowledge = [
        """DIABETES - REGRA FUNDAMENTAL:
SE paciente USA INSULINA = E10.0 (diabetes insulino-dependente)
SE paciente NÃO USA INSULINA = E11.0 (diabetes não-insulino-dependente)

E10.0 - Diabetes mellitus insulino-dependente com coma
E10.1 - Diabetes mellitus insulino-dependente com cetoacidose
E10.2 - Diabetes mellitus insulino-dependente com complicações renais
E10.3 - Diabetes mellitus insulino-dependente com complicações oftálmicas
E10.4 - Diabetes mellitus insulino-dependente com complicações neurológicas
E10.9 - Diabetes mellitus insulino-dependente sem complicações

PALAVRAS-CHAVE: diabetes tipo 1, insulina, aplico insulina, uso insulina, injeto insulina, insulina diariamente""",

        """E11.0 - Diabetes mellitus não-insulino-dependente com coma
E11.1 - Diabetes mellitus não-insulino-dependente com cetoacidose
E11.2 - Diabetes mellitus não-insulino-dependente com complicações renais
E11.3 - Diabetes mellitus não-insulino-dependente com complicações oftálmicas
E11.4 - Diabetes mellitus não-insulino-dependente com complicações neurológicas
E11.9 - Diabetes mellitus não-insulino-dependente sem complicações

PALAVRAS-CHAVE: diabetes tipo 2, metformina, glicazida, gliclazida, comprimidos diabetes, sem insulina""",

        """HIPERTENSÃO:
I10 - Hipertensão essencial
I11.0 - Doença cardíaca hipertensiva com insuficiência cardíaca
I11.9 - Doença cardíaca hipertensiva sem insuficiência cardíaca
I12.0 - Doença renal hipertensiva com insuficiência renal
I12.9 - Doença renal hipertensiva sem insuficiência renal

PALAVRAS-CHAVE: pressão alta, hipertensão, pressão arterial, losartana, captopril, enalapril, amlodipina, atenolol""",

        """DEPRESSÃO:
F32.0 - Episódio depressivo leve
F32.1 - Episódio depressivo moderado
F32.2 - Episódio depressivo grave sem sintomas psicóticos
F32.3 - Episódio depressivo grave com sintomas psicóticos
F33.0 - Transtorno depressivo recorrente, episódio atual leve
F33.1 - Transtorno depressivo recorrente, episódio atual moderado
F33.2 - Transtorno depressivo recorrente, episódio atual grave

PALAVRAS-CHAVE: depressão, tristeza, melancolia, desânimo, fluoxetina, sertralina, escitalopram, venlafaxina, antidepressivo""",

        """ANSIEDADE E PÂNICO:
F41.0 - Transtorno de pânico (ansiedade paroxística episódica)
F41.1 - Ansiedade generalizada
F41.2 - Transtorno misto ansioso e depressivo
F41.3 - Outros transtornos ansiosos mistos
F41.8 - Outros transtornos ansiosos especificados
F41.9 - Transtorno ansioso não especificado

PALAVRAS-CHAVE: ansiedade, pânico, crise de ansiedade, nervosismo, medo, fobia, clonazepam, alprazolam, lorazepam""",

        """CARDIOLOGIA:
I21.0 - Infarto agudo do miocárdio da parede anterior
I21.1 - Infarto agudo do miocárdio da parede inferior
I21.2 - Infarto agudo do miocárdio de outras localizações
I21.3 - Infarto agudo do miocárdio de localização não especificada
I21.4 - Infarto subendocárdico agudo do miocárdio
I21.9 - Infarto agudo do miocárdio não especificado

I25.0 - Aterosclerose coronariana
I25.1 - Doença aterosclerótica do coração
I25.2 - Infarto antigo do miocárdio

PALAVRAS-CHAVE: infarto, enfarte, coração, cardíaco, angina, dor no peito, cateterismo""",

        """ORTOPEDIA:
M51.0 - Transtornos de discos lombares e outros discos intervertebrais com mielopatia
M51.1 - Transtornos de discos lombares e outros discos intervertebrais com radiculopatia
M51.2 - Outros deslocamentos especificados de disco intervertebral
M51.3 - Outra degeneração especificada de disco intervertebral
M51.4 - Nódulos de Schmorl
M51.8 - Outros transtornos especificados de discos intervertebrais
M51.9 - Transtorno de disco intervertebral não especificado

S72.0 - Fratura do colo do fêmur
S72.1 - Fratura pertrocantérica
S72.2 - Fratura subtrocantérica do fêmur

PALAVRAS-CHAVE: hérnia de disco, coluna, lombar, cervical, dor nas costas, ciática, fratura, quebrou osso""",

        """NEUROLOGIA:
I64 - Acidente vascular cerebral não especificado como hemorrágico ou isquêmico
I63.0 - Infarto cerebral devido a trombose de artérias pré-cerebrais
I63.1 - Infarto cerebral devido a embolia de artérias pré-cerebrais
I63.9 - Infarto cerebral não especificado

G40.0 - Epilepsia e síndromes epilépticas idiopáticas localizadas
G40.1 - Epilepsia e síndromes epilépticas sintomáticas localizadas
G40.2 - Epilepsia e síndromes epilépticas sintomáticas localizadas
G40.9 - Epilepsia não especificada

PALAVRAS-CHAVE: AVC, derrame, acidente vascular cerebral, isquemia cerebral, epilepsia, convulsão, crise convulsiva"""
    ]
    
    # Tentar adicionar CIDs do arquivo
    try:
        print("📄 Lendo arquivo CID...")
        with open('CID-10-SUBCATEGORIAS.CSV', 'r', encoding='iso-8859-1') as f:
            reader = csv.reader(f, delimiter=';')
            
            chunk = ""
            count = 0
            
            for row in reader:
                if len(row) >= 2:
                    codigo = row[0].strip()
                    descricao = row[1].strip()
                    
                    # Aceitar QUALQUER CID válido
                    if (codigo and len(codigo) >= 3 and 
                        descricao and len(descricao) > 3):
                        
                        line = f"{codigo} - {descricao}"
                        
                        if len(chunk + line) < 800:
                            chunk += line + "\n"
                        else:
                            if chunk.strip():
                                base_knowledge.append(chunk.strip())
                            chunk = line + "\n"
                        
                        count += 1
                        
                        # Limite para não sobrecarregar
                        if count >= 5000:
                            break
            
            # Adicionar último chunk
            if chunk.strip():
                base_knowledge.append(chunk.strip())
                
            print(f"✅ Adicionados {count} CIDs do arquivo")
            
    except Exception as e:
        print(f"⚠️ Erro lendo CSV: {e}")
        print("📝 Usando apenas conhecimento base")
    
    print(f"📚 Total de chunks: {len(base_knowledge)}")
    return base_knowledge

def create_faiss_index():
    """Cria índice FAISS com conhecimento médico"""
    
    print("🧠 Criando índice FAISS...")
    
    # Verificar API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY necessária!")
        return False
    
    client = OpenAI(api_key=api_key)
    
    # Criar conhecimento
    chunks = create_medical_knowledge()
    
    if len(chunks) < 5:
        print(f"❌ Poucos chunks: {len(chunks)}")
        return False
    
    print(f"🔄 Gerando {len(chunks)} embeddings...")
    
    # Gerar embeddings
    embeddings = []
    for i, chunk in enumerate(chunks):
        print(f"   {i+1}/{len(chunks)}", end='\r')
        
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            )
            embeddings.append(response.data[0].embedding)
        except Exception as e:
            print(f"\n❌ Erro embedding {i+1}: {e}")
            return False
    
    print(f"\n✅ Embeddings gerados!")
    
    # Criar índice FAISS
    embeddings_array = np.array(embeddings, dtype=np.float32)
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    # Preparar diretório
    index_dir = "app/index_faiss_openai"
    os.makedirs(index_dir, exist_ok=True)
    
    # Salvar
    index_path = os.path.join(index_dir, "index.faiss")
    docs_path = os.path.join(index_dir, "documents.pkl")
    
    faiss.write_index(index, index_path)
    
    with open(docs_path, 'wb') as f:
        pickle.dump(chunks, f)
    
    # Estatísticas finais
    file_size = os.path.getsize(index_path) / 1024 / 1024
    
    print(f"✅ FAISS criado com SUCESSO!")
    print(f"📊 Vetores: {index.ntotal}")
    print(f"📄 Documentos: {len(chunks)}")
    print(f"💾 Tamanho: {file_size:.1f} MB")
    print(f"📁 Salvo em: {index_dir}")
    
    return True

if __name__ == "__main__":
    print("🚀 CRIAÇÃO FINAL DO SISTEMA FAISS")
    print("=" * 45)
    
    if create_faiss_index():
        print("\n🎯 SUCESSO COMPLETO!")
        print("✅ Sistema FAISS criado")
        print("🧠 Conhecimento médico carregado")
        print("🚀 RAG funcionando!")
        print("\n📋 PRÓXIMO PASSO:")
        print("   Testar classificação da Helena!")
    else:
        print("\n❌ Falha na criação")
