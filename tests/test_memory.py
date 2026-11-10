from cineagents.memory import Memory


def test_preferences_update_preserve_provenance_and_user_isolation(tmp_path):
    memory=Memory(tmp_path/'memory.db')
    memory.set_preference(1,'genre','Comedy','explicit user input',now=100)
    memory.set_preference(1,'genre','Drama','explicit correction',now=101)
    assert memory.preferences(1,now=102)['genre']['value']=='Drama'
    assert memory.preferences(1,now=102)['genre']['source']=='explicit correction'
    assert memory.preferences(2,now=102)=={}


def test_expired_memory_is_removed_and_delete_clears_both_layers(tmp_path):
    memory=Memory(tmp_path/'memory.db')
    memory.set_preference(1,'genre','Drama','input',ttl=10,now=100)
    memory.add_episode(1,{'movie_ids':[2,3]},ttl=5,now=100)
    assert len(memory.episodes(1,now=104))==1
    assert memory.episodes(1,now=106)==[]
    assert memory.preferences(1,now=111)=={}
    memory.add_episode(1,{'movie_ids':[4]},now=112)
    memory.delete_user(1)
    assert memory.episodes(1,now=113)==[]
