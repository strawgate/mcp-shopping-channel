"""Seed products for EVOLVE-O-MART."""

from evolve_o_mart.models import Product

SEED_PRODUCTS: list[Product] = [
    Product(
        id="prod_001",
        name="Steam Bowl",
        tagline="A bowl. With steam.",
        description="A perfectly ordinary ceramic bowl that happens to emit a constant, gentle steam. Nobody knows why. Nobody asks.",
        ascii_art=r"""
    .-~~~-.
   /       \
  |  ~   ~  |
   \       /
    '-----'
   (  steam )
    ~~~~~~~~
        """,
    ),
    Product(
        id="prod_002",
        name="The Uncertainty Lamp",
        tagline="Is it on? Is it off? Yes.",
        description=(
            "A lamp that exists in a superposition of on and off states until you look directly at it. "
            "Then it's definitely one of those. Probably."
        ),
        ascii_art=r"""
       ___
      /   \
     |     |
     |  ?  |
      \   /
       | |
      /   \
     /_____\
        """,
    ),
    Product(
        id="prod_003",
        name="Regret Pencil",
        tagline="Write now, apologize later.",
        description="Every mark this pencil makes automatically includes a tiny apology. Perfect for passive-aggressive note-leaving.",
        ascii_art=r"""
           __
          /  |
         /   |
        /    |
       /  __ |
      / /   \|
     /_/sorry\
        """,
    ),
    Product(
        id="prod_004",
        name="Motivational Brick",
        tagline="You can do it. Probably.",
        description="A brick that whispers encouragement when you hold it. The encouragement is vague and sometimes concerning.",
        ascii_art=r"""
    ___________
   /          /|
  /  YOU GOT / |
 /   THIS   /  |
|__________|   |
|          |  /
|  (maybe) | /
|__________|/
        """,
    ),
    Product(
        id="prod_005",
        name="Procrastination Clock",
        tagline="There's always tomorrow.",
        description="A clock that's perpetually 5 minutes behind schedule. Not broken—just not ready yet. Will sync up eventually. Probably.",
        ascii_art=r"""
      .---.
     /     \
    |  12   |
    | 9  3  |
    |   6   |
     \ ... /
      '---'
    (later)
        """,
    ),
    Product(
        id="prod_006",
        name="Existential Sponge",
        tagline="Absorbs liquids and meaning.",
        description="A sponge that quietly questions its purpose while cleaning. 'Am I removing dirt, or am I the dirt?' it wonders. Still works great on dishes.",
        ascii_art=r"""
    .--------.
   /  why?   /|
  /  ~~~~   / |
 |  o _ o  |  |
 | (     ) |  /
 |  ~~~~   | /
 |_________|/
        """,
    ),
]
