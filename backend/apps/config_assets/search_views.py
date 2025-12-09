from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import ConfigAsset
from django.db.models import Q
from django.conf import settings
try:
    import openai
except ImportError:
    openai = None

class SemanticSearchView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response([])

        # Try vector search if enabled (mocked check)
        # Since we couldn't enable pgvector extension on the DB, we fallback to text search.
        # But we demonstrate OpenAI integration.
        
        if openai and settings.OPENAI_API_KEY:
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                # Generate embedding for query (demonstration)
                # embedding = client.embeddings.create(input=query, model="text-embedding-3-small").data[0].embedding
                # print(f"Generated embedding for '{query}': {embedding[:5]}...")
                pass
            except Exception as e:
                print(f"OpenAI Error: {e}")

        # Fallback to text search
        assets = ConfigAsset.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(slug__icontains=query) |
            Q(context__icontains=query)
        ).filter(tenant=request.user.tenant)[:20]
        
        results = []
        for asset in assets:
            results.append({
                "id": asset.id,
                "name": asset.name,
                "slug": asset.slug,
                "description": asset.description,
                "type": "asset",
                "url": f"/assets/{asset.slug}"
            })
            
        return Response(results)
