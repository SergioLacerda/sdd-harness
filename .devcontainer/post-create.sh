#!/bin/bash
set -e

echo "🚀 Configurando ambiente SDD Harness..."

# Instala uv via pip (sem curl-pipe-to-shell; PyPI verifica assinaturas do pacote)
python3 -m pip install --quiet uv

# Sincroniza dependências
uv sync --all-groups

# Instala pre-commit hooks
uv run pre-commit install --install-hooks

# Verifica se o SDD CLI está funcionando
echo "✅ Verificando SDD CLI..."
uv run sdd --version || echo "⚠️  SDD CLI ainda não instalado como pacote editável"

echo "=========================================="
echo "✅ Ambiente SDD Harness configurado com sucesso!"
echo "Comandos úteis:"
echo "   uv run sdd doctor run"
echo "   uv run sdd governance compile"
echo "   make help"
echo "=========================================="
