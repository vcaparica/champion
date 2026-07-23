"""Tests for the Feat data model and loader."""
import json
import os
import tempfile
from game.feat import Reaction, Feat, load_feat, load_all_feats


FEAT_JSON = {
    "id": "iron_composure",
    "name": "Iron Composure",
    "description": "Calm hardens with every blow. | Each time struck, +1 damage reduction, up to +3.",
    "reactions": [
        {"trigger": "take_damage", "effect": "damage_reduction_lasting", "value": 1, "max_stacks": 3}
    ],
}


def test_reaction_defaults():
    r = Reaction(trigger="deal_damage", effect="bonus_outgoing")
    assert r.value == 0
    assert r.scales_with is None
    assert r.once_per is None
    assert r.rider_power == 0


def test_feat_holds_reactions():
    feat = Feat(id="x", name="X", description="d", reactions=[Reaction("take_damage", "heal", value=5)])
    assert feat.reactions[0].effect == "heal"
    assert feat.reactions[0].value == 5


def test_load_feat_from_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FEAT_JSON, f)
        path = f.name
    try:
        feat = load_feat(path)
        assert feat.id == "iron_composure"
        assert feat.name == "Iron Composure"
        assert len(feat.reactions) == 1
        r = feat.reactions[0]
        assert r.trigger == "take_damage"
        assert r.effect == "damage_reduction_lasting"
        assert r.value == 1
        assert r.max_stacks == 3
    finally:
        os.unlink(path)


def test_load_feat_optional_fields_default():
    data = dict(FEAT_JSON)
    data["reactions"] = [{"trigger": "deal_damage", "effect": "bonus_outgoing", "scales_with": "half_speed"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        feat = load_feat(path)
        r = feat.reactions[0]
        assert r.scales_with == "half_speed"
        assert r.value == 0
        assert r.cap is None
    finally:
        os.unlink(path)


def test_load_all_feats():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "a.json"), "w") as f:
            json.dump(FEAT_JSON, f)
        with open(os.path.join(tmp, "b.json"), "w") as f:
            json.dump(dict(FEAT_JSON, id="bladestorm", name="Bladestorm"), f)
        feats = load_all_feats(tmp)
        assert len(feats) == 2
        assert "iron_composure" in feats
        assert "bladestorm" in feats


def test_load_all_feats_missing_dir_returns_empty():
    assert load_all_feats("game/data/does_not_exist_xyz") == {}
