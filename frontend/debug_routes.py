#!/usr/bin/env python3

print("🔍 DEBUG DAS ROTAS DO FLASK")
print("=" * 50)

try:
    import app
    print("✅ app.py importado com sucesso")
    
    print("\n📋 ROTAS REGISTRADAS:")
    for rule in app.app.url_map.iter_rules():
        methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"  {rule.rule:<30} → {rule.endpoint:<20} [{methods}]")
    
    print(f"\n🌐 CONFIGURAÇÃO:")
    print(f"  Debug: {app.app.debug}")
    print(f"  Host: 0.0.0.0")
    print(f"  Port: 5003")
    
    print(f"\n📁 TEMPLATES:")
    import os
    template_dir = app.app.template_folder
    if os.path.exists(template_dir):
        templates = os.listdir(template_dir)
        for template in templates:
            size = os.path.getsize(os.path.join(template_dir, template))
            print(f"  {template:<30} → {size} bytes")
    else:
        print(f"  ❌ Pasta templates não encontrada: {template_dir}")
    
    print(f"\n🔧 BACKEND URL:")
    print(f"  {app.BACKEND_URL}")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
