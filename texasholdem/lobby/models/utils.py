
import uuid

def generate_slug(model) -> str:
    """Generate a unique slug
        Args:
            model (cls): Django Model
        Returns:
            slug (string)
    """
    query_manager = model.objects
    slug = uuid.uuid4().hex[:6]
    while query_manager.filter(slug=slug).exists():
        slug = uuid.uuid4().hex[:6]
    return slug
