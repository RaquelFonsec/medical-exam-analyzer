#!/usr/bin/env python3
"""
Teste final completo da integração RAG + MultimodalAIService
"""

import os
import sys
import asyncio
from datetime import datetime

# Adicionar caminho do projeto
sys.path.append('/home/raquel/medical-exam-analyzer/backend')

async def test_complete_multimodal_analysis():
    """Teste completo da análise multimodal com RAG"""
    
    print("🧪 TESTE FINAL - ANÁLISE MULTIMODAL COMPLETA COM RAG")
    print("="*60)
    
    try:
        from app.services.multimodal_ai_service import multimodal_ai_service
        
        # Casos de teste completos
        test_cases = [
            {
                'name': 'Helena - Pedreira (Caso Ortopédico)',
                'patient_info': 'helena silva 45 anos',
                'transcription': '''Doutor, sou Helena Silva, tenho 45 anos, trabalho como pedreira há 20 anos na construção civil. 
                Há 2 anos, durante o trabalho carregando materiais pesados, machuquei a coluna. 
                Desde então tenho dor lombar constante que piora quando faço esforço. 
                Não consigo mais carregar nem uma sacola de compras. 
                A dor é insuportável e não aguento mais trabalhar na obra. 
                Quero me aposentar por invalidez porque não tenho condições de continuar trabalhando.''',
                'expected': {
                    'specialty': 'Ortopedia',
                    'condition_keywords': ['lombar', 'coluna', 'ocupacional'],
                    'severity': ['Alta', 'Muito Alta']
                }
            },
            {
                'name': 'Carlos - Motorista (Caso Cardiológico)',
                'patient_info': 'carlos santos 48 anos',
                'transcription': '''Doutor, me chamo Carlos Santos, tenho 48 anos, sou motorista de caminhão há 25 anos. 
                Há 4 meses tive um infarto do miocárdio e desde então não consigo mais fazer esforço físico. 
                Qualquer esforço me deixa ofegante e com dor no peito. 
                Tenho pressão alta que não controla nem com remédio. 
                Não posso mais dirigir caminhão porque não aguento o esforço e tenho medo de passar mal no volante. 
                Preciso de auxílio-doença porque não tenho condições de trabalhar.''',
                'expected': {
                    'specialty': 'Cardiologia',
                    'condition_keywords': ['cardiovascular', 'infarto', 'isquêmica'],
                    'severity': ['Alta', 'Muito Alta']
                }
            }
        ]
        
        results = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n{'='*20} TESTE {i}: {case['name']} {'='*20}")
            print(f"Patient Info: {case['patient_info']}")
            print(f"Transcrição: {case['transcription'][:100]}...")
            
            # Executar análise multimodal completa
            result = await multimodal_ai_service.analyze_multimodal(
                patient_info=case['patient_info'],
                transcription=case['transcription']
            )
            
            # Analisar resultados
            success = result.get('success', False)
            specialty = result.get('especialidade', 'N/A')
            condition = result.get('dados_extraidos', {}).get('condicao_medica', '').lower()
            severity = result.get('dados_extraidos', {}).get('gravidade', 'N/A')
            name = result.get('dados_extraidos', {}).get('nome', 'N/A')
            
            print(f"\n📊 RESULTADOS DA ANÁLISE:")
            print(f"   ✅ Sucesso: {success}")
            print(f"   👤 Nome: {name}")
            print(f"   🏥 Especialidade: {specialty}")
            print(f"   🔍 Condição: {condition[:50]}...")
            print(f"   ⚠️ Gravidade: {severity}")
            
            # Verificar se especialidade está correta
            expected_specialty = case['expected']['specialty']
            if specialty == expected_specialty:
                print(f"   🎯 ESPECIALIDADE CORRETA!")
            else:
                print(f"   ❌ Especialidade incorreta - Esperado: {expected_specialty}")
            
            # Verificar condição
            condition_match = any(keyword in condition for keyword in case['expected']['condition_keywords'])
            if condition_match:
                print(f"   🎯 CONDIÇÃO CORRETA!")
            else:
                print(f"   ❌ Condição pode estar incorreta")
            
            results.append({
                'case': case['name'],
                'success': success,
                'specialty_correct': specialty == expected_specialty,
                'condition_match': condition_match
            })
        
        # Resumo final
        print(f"\n{'='*60}")
        print("📊 RESUMO FINAL DOS TESTES")
        print("="*60)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['success'])
        correct_specialties = sum(1 for r in results if r['specialty_correct'])
        correct_conditions = sum(1 for r in results if r['condition_match'])
        
        print(f"✅ Testes executados com sucesso: {successful_tests}/{total_tests}")
        print(f"🎯 Especialidades corretas: {correct_specialties}/{total_tests}")
        print(f"🔍 Condições corretas: {correct_conditions}/{total_tests}")
        
        if successful_tests == total_tests and correct_specialties >= total_tests * 0.8:
            print(f"\n🎉 SISTEMA RAG FUNCIONANDO PERFEITAMENTE!")
            print("✅ Integração RAG + MultimodalAIService concluída com sucesso")
            return True
        else:
            print(f"\n⚠️ Sistema precisa de ajustes")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste final: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🚀 EXECUTANDO TESTE FINAL DO SISTEMA RAG")
    return asyncio.run(test_complete_multimodal_analysis())

if __name__ == "__main__":
    main()