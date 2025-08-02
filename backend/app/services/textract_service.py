# ============================================================================
# AWS TEXTRACT SERVICE COM DEBUG MELHORADO
# ============================================================================

import os
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

logger = logging.getLogger(__name__)

class TextractExamService:
    """Serviço AWS Textract com debug melhorado"""
    
    def __init__(self):
        self.client = None
        self.supported_formats = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        self._init_client_with_debug()
    
    def _init_client_with_debug(self):
        """Inicializa cliente AWS com debug detalhado"""
        try:
            # Debug das variáveis de ambiente
            logger.info("🔍 Verificando credenciais AWS...")
            
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION')
            
            logger.info(f"📋 AWS_ACCESS_KEY_ID: {'✅ Presente' if aws_access_key else '❌ Ausente'}")
            logger.info(f"📋 AWS_SECRET_ACCESS_KEY: {'✅ Presente' if aws_secret_key else '❌ Ausente'}")
            logger.info(f"📋 AWS_REGION: {aws_region if aws_region else '❌ Ausente'}")
            
            if aws_access_key:
                logger.info(f"🔑 Access Key preview: {aws_access_key[:8]}...{aws_access_key[-4:]}")
            
            # Tentar diferentes métodos de configuração
            
            # Método 1: Explicit credentials
            if aws_access_key and aws_secret_key and aws_region:
                try:
                    logger.info("🔄 Tentando configuração explícita...")
                    session = boto3.Session(
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key,
                        region_name=aws_region
                    )
                    
                    self.client = session.client('textract')
                    
                    # Teste básico
                    caller_identity = session.client('sts').get_caller_identity()
                    logger.info(f"✅ AWS configurado com sucesso!")
                    logger.info(f"👤 User ARN: {caller_identity.get('Arn', 'N/A')}")
                    logger.info(f"🏢 Account: {caller_identity.get('Account', 'N/A')}")
                    return
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    logger.error(f"❌ Erro de cliente AWS: {error_code}")
                    
                    if error_code == 'InvalidUserID.NotFound':
                        logger.error("💡 As credenciais parecem estar incorretas ou o usuário não existe")
                    elif error_code == 'SignatureDoesNotMatch':
                        logger.error("💡 A chave secreta está incorreta")
                    elif error_code == 'InvalidAccessKeyId':
                        logger.error("💡 O Access Key ID está incorreto")
                    elif error_code == 'TokenRefreshRequired':
                        logger.error("💡 As credenciais expiraram")
                    
                except Exception as e:
                    logger.error(f"❌ Erro inesperado: {e}")
            
            # Método 2: Default credentials (se existir ~/.aws/credentials)
            try:
                logger.info("🔄 Tentando configuração padrão...")
                session = boto3.Session()
                
                # Verificar se tem credenciais padrão
                session.get_credentials()
                
                if aws_region:
                    self.client = session.client('textract', region_name=aws_region)
                else:
                    self.client = session.client('textract')
                
                # Teste
                caller_identity = session.client('sts').get_caller_identity()
                logger.info(f"✅ AWS configurado via perfil padrão!")
                logger.info(f"👤 User ARN: {caller_identity.get('Arn', 'N/A')}")
                return
                
            except (NoCredentialsError, PartialCredentialsError):
                logger.warning("⚠️ Credenciais padrão não encontradas")
            except Exception as e:
                logger.error(f"❌ Erro na configuração padrão: {e}")
            
            # Se chegou até aqui, falhou
            logger.error("❌ Falha em todas as tentativas de configuração AWS")
            self.client = None
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização AWS: {e}")
            self.client = None
    
    def test_textract_connection(self) -> dict:
        """Testa conexão com Textract"""
        if not self.client:
            return {
                'success': False,
                'error': 'Cliente não inicializado'
            }
        
        try:
            # Criar um teste mínimo
            test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
            
            response = self.client.detect_document_text(
                Document={'Bytes': test_image}
            )
            
            return {
                'success': True,
                'response_id': response.get('DocumentMetadata', {}).get('Pages', 0)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# ============================================================================
# ENDPOINT DE DEBUG AWS
# ============================================================================

@app.get("/api/debug-aws")
async def debug_aws():
    """🔍 Debug das configurações AWS"""
    
    # Recriar serviço para debug
    debug_service = TextractExamService()
    
    # Teste de conexão
    test_result = debug_service.test_textract_connection()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'environment_variables': {
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID')[:8] + '...' if os.getenv('AWS_ACCESS_KEY_ID') else None,
            'AWS_SECRET_ACCESS_KEY': '✅ Present' if os.getenv('AWS_SECRET_ACCESS_KEY') else '❌ Missing',
            'AWS_REGION': os.getenv('AWS_REGION'),
            'AWS_DEFAULT_REGION': os.getenv('AWS_DEFAULT_REGION')
        },
        'boto3_info': {
            'version': boto3.__version__,
            'default_session_region': boto3.Session().region_name
        },
        'textract_test': test_result,
        'recommendations': [
            'Verificar se as credenciais não expiraram',
            'Confirmar que o usuário tem permissão para Textract',
            'Testar com AWS CLI: aws sts get-caller-identity',
            'Verificar se a região está correta'
        ]
    }

# ============================================================================
# ENDPOINT DE CONFIGURAÇÃO AWS
# ============================================================================

@app.post("/api/configure-aws")
async def configure_aws(
    access_key: str = Form(...),
    secret_key: str = Form(...),
    region: str = Form(default="us-east-2")
):
    """🔧 Configurar AWS dinamicamente (apenas para debug)"""
    
    try:
        # Configurar temporariamente
        os.environ['AWS_ACCESS_KEY_ID'] = access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
        os.environ['AWS_REGION'] = region
        
        # Recriar serviço
        global textract_service
        textract_service = TextractExamService()
        
        # Testar
        test_result = textract_service.test_textract_connection()
        
        return {
            'success': test_result.get('success', False),
            'message': 'Configuração atualizada' if test_result.get('success') else 'Falha na configuração',
            'test_result': test_result
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 