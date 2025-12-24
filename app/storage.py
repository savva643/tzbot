from sqlalchemy import select, func

from .models import Message, StarsTransaction, User

# все связанное с хранилищем

async def get_or_create_user(session, tg_id, default_model):
    stmt = select(User).where(User.tg_id == tg_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user:
        return user
    user = User(tg_id=tg_id, model_name=default_model)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_model(session, user, model_name):
    user.model_name = model_name
    await session.commit()
    await session.refresh(user)
    return user


async def grant_access(session, user):
    user.has_access = True
    await session.commit()
    await session.refresh(user)
    return user


async def add_message(session, user_id, role, content, model_name):
    msg = Message(user_id=user_id, role=role, content=content, model_name=model_name)
    session.add(msg)
    await session.commit()
    return msg


async def get_last_history(session, user_id, model_name, limit=5):
    stmt = (
        select(Message)
        .where(Message.user_id == user_id, Message.model_name == model_name)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return list(reversed(rows))


async def add_stars(session, user, amount):
    user.stars_balance += amount
    await session.commit()
    await session.refresh(user)
    return user.stars_balance


async def spend_stars(session, user, amount):
    if user.stars_balance < amount:
        return False
    user.stars_balance -= amount
    await session.commit()
    await session.refresh(user)
    return True


async def save_stars_transaction(session, user_id, product_id, stars_amount, payload, currency, charge_id):
    tx = StarsTransaction(
        user_id=user_id,
        product_id=product_id,
        stars_amount=stars_amount,
        payload=payload,
        currency=currency,
        tg_charge_id=charge_id,
    )
    session.add(tx)
    await session.commit()
    return tx


async def user_stats(session):
    total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
    total_stars = (await session.execute(select(func.coalesce(func.sum(User.stars_balance), 0)))).scalar_one()
    tx_count = (await session.execute(select(func.count(StarsTransaction.id)))).scalar_one()
    return {"users": total_users, "stars": total_stars, "transactions": tx_count}


async def last_transactions(session, limit=20):
    stmt = select(StarsTransaction).order_by(StarsTransaction.created_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()
