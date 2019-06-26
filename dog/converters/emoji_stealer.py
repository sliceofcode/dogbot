import re
from typing import Optional

import discord
import lifesaver
from discord import PartialEmoji
from discord.ext import commands
from lifesaver.utils import history_reducer

EMOJI_REGEX = re.compile(r"""
    # A Discord emoji, as represented in raw message content.

    <
        # Animation flag
        (?P<animated>a?)
        :

        # Emoji name
        (?P<name>\w+)
        :

        # Emoji ID
        (?P<id>\d+)
    >
""", re.VERBOSE)

EMOJI_URL_REGEX = re.compile(r"""
    # A Discord emoji URL.

    # The standard part of the URL
    ^https?://
    cdn\.discordapp\.com
    /emojis/

    # Emoji ID
    (?P<id>\d+)

    # File extension
    \.
    (?P<extension>png|gif)
""", re.VERBOSE)


class EmojiStealer(commands.Converter):
    """A versatile converter intended to convert into :class:`discord.PartialEmoji`.

    The argument can be an emoji (as used normally), an emoji ID, or an emoji
    URL. If the string "recent" is passed, then the converter will scan for
    recently used custom emoji in the current channel to resolve. If there are
    multiple, the user is interactively prompted for selection.
    """

    @staticmethod
    async def recent(ctx: lifesaver.Context) -> PartialEmoji:
        def reducer(msg: discord.Message) -> Optional[PartialEmoji]:
            match = EMOJI_REGEX.search(msg.content)

            if not match:
                return None

            emoji_id = int(match.group('id'))

            # If the emoji used is already in the guild, ignore.
            if emoji_id in {emoji.id for emoji in ctx.guild.emojis}:
                return None

            return PartialEmoji(
                animated=bool(match.group('animated')),
                name=match.group('name'),
                id=emoji_id,
            )

        results = await history_reducer(ctx, reducer, ignore_duplicates=True, limit=10)

        if not results:
            raise commands.BadArgument('No stealable custom emoji were found.')

        if len(results) > 1:
            result = await ctx.pick_from_list(results)
        else:
            result = results[0]

        return result

    async def convert(self, ctx: lifesaver.Context, argument: str) -> PartialEmoji:
        # Convert an emoji ID.
        if argument.isdigit():
            return PartialEmoji(id=int(argument), name=None, animated=False)

        # Convert from an emoji URL.
        url_match = EMOJI_URL_REGEX.search(argument)
        if url_match:
            return PartialEmoji(
                id=int(url_match.group('id')),
                name=None,
                animated=url_match.group('extension') == 'png',
            )

        # Convert an actual emoji.
        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.BadArgument:
            pass

        # Scan recently used custom emoji.
        if argument == 'recent':
            return await self.recent(ctx)

        raise commands.BadArgument(
            'Invalid emoji. You can use an actual emoji or an emoji ID or URL. '
            'You can also specify `recent` to select a recently used emoji.')