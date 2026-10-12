def reviewed_confirm(client, path, *, json):
    """Exercise the public review contract before an intended confirmation."""
    reviewed = client.post(path.removesuffix('/confirm')+'/review', json={'player_ids': json['player_ids']})
    if reviewed.status_code != 200:
        return reviewed
    return client.post(path, json={**json, 'review_token': reviewed.json()['review_token']})
