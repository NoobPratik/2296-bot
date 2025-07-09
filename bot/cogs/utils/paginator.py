from typing import Optional, List, Union
from discord import Interaction, SelectOption, User, ButtonStyle
from discord.ui import View, Select, button, Button


class PageSelect(Select):
    def __init__(self, pages: List[SelectOption]):
        super().__init__(placeholder="Quick navigation",
                         min_values=1, max_values=1, options=pages, row=0)

    async def callback(self, interaction: Interaction):
        self.view.current_page = int(self.values[0])

        await self.view.update_children(interaction)


class PageView(View):
    def __init__(self, author: User, pages: List[SelectOption], limited: bool):
        super().__init__(timeout=180)
        self.author = author
        self.pages = pages
        self.current_page = 0
        self.limited = limited
        self.next_page_callback = None
        self.page_offset = 1
        self.label.label = f'{self.current_page + 1}/{len(self.pages)}' if self.limited else self.current_page+1

    async def interaction_check(self, itr: Interaction) -> bool:
        return itr.user.id == self.author.id

    async def update_children(self, itr: Interaction):
        self.label.label = f'{self.current_page + 1}/{len(self.pages)}' if self.limited else self.current_page+1
        self.next.disabled = (self.current_page + 1 == len(self.pages) and self.limited) 
        self.last.disabled = (self.current_page + 1 == len(self.pages) and self.limited) 
        self.previous.disabled = (self.current_page <= 0)
        self.first.disabled = (self.current_page <= 0)

        await itr.response.edit_message(embed=self.pages[self.current_page], view=self)

    @button(label="◀◀", style=ButtonStyle.gray, row=1)
    async def first(self, itr: Interaction, _: Button):
        self.current_page = 0

        await self.update_children(itr)

    @button(label="◀", style=ButtonStyle.blurple, row=1)
    async def previous(self, itr: Interaction, _: Button):
        self.current_page -= 1

        await self.update_children(itr)

    @button(label="1/5", style=ButtonStyle.blurple, row=1, disabled=True)
    async def label(self, __: Interaction, _: Button):
        self.stop()

    @button(label="▶", style=ButtonStyle.blurple, row=1)
    async def next(self, itr: Interaction, _: Button):
        self.current_page += 1

        if self.current_page >= len(self.pages) and self.next_page_callback:
            new_pages = await self.next_page_callback(self.page_offset + 1)
            if new_pages:
                self.page_offset += 1
                self.pages.extend(new_pages)
            else:
                self.current_page = len(self.pages) - 1

        await self.update_children(itr)

    @button(label="▶▶", style=ButtonStyle.gray, row=1)
    async def last(self, itr: Interaction, _: Button):
        self.current_page = len(self.pages) - 1

        await self.update_children(itr)


class Paginator:
    def __init__(
            self, itr: Interaction, pages: list,
            custom_children: Optional[List[Union[Button, Select]]] = None, 
            limited: bool = True, next_page_callback=None
    ):
        self.custom_children = custom_children or []
        self.itr = itr
        self.pages = pages
        self.next_page_callback = next_page_callback
        self.limited = limited

    async def start(self, quick_navigation: bool = False) -> None:
        if len(self.pages) == 1:
            await self.itr.edit_original_response(embed=self.pages[0], view=None)
            return

        view = PageView(self.itr.user, self.pages, limited=self.limited)
        view.next_page_callback = self.next_page_callback

        view.previous.disabled = view.current_page <= 0
        view.next.disabled = ((view.current_page+1) >= len(self.pages) and self.limited)

        if quick_navigation:
            options = [SelectOption(label=f"Page {index}", value=f"{index}") for index in range(len(self.pages), 1)]
            view.add_item(PageSelect(options))

        if len(self.custom_children) > 0:
            for child in self.custom_children:
                view.add_item(child)

        try:
            embed = self.pages[view.current_page]
        except IndexError:
            embed = None

        await self.itr.edit_original_response(content='\u200b', embed=embed, view=view if embed else None)
        if embed:
            await view.wait()

            for child in view.children:
                child.disabled = True

            await self.itr.edit_original_response(content='\u200b', embed=embed, view=view)
