## PSearch.vim

**v0.3**


### Overview

This plugin shows a preview of all the lines where your search
pattern matches in the currently opened buffers. 

![Screenshot](/extra/screenshot.png "A view of the plugin at work")  

Execute the `:PSearch` command and type something. You'll see a preview 
of all the lines where the pattern you gave matches in the currently 
opened buffers.

Below there is list of all the mappings you can use to interact with the window:

* `UP`, `CTRL+K`: move up in the list.
* `DOWN`, `CTRL+J`: move down in the list.
* `CTRL+B`: move to the bottom of the list.
* `CTRL+T`: move to the top of the list.
* `LEFT` or `CTRL+H`, `RIGHT` or `CTRL+L`: move across lists of matches of other buffers.
* `RETURN`, `CTRL+G`: go to the selected match.
* `CTRL+A`: show jump marks for each result.
* `ESC`, `CTRL+C`: close the matches list.

You are allowed to use any pattern that would work with the `/` and
`?` vim commands and as the `nomagic` option would be set.

Pressing `CTRL+A` in the psearch navigation buffer will add jump marks denoted
in the format `<[a-z]>` for each search result entry. When the marks have been
displayed entering any of the letters used as mark will jump directly to the
respective entry and close the search navigation. Entering any letter that is
not a mark will discard the action.


## Requirements

* Vim 7.2+
* Vim compiled with python 2.6+


## Installation

Extract the content of the folder into the `$HOME/.vim` directory or use your favourite
plugin manager.



## Commands

### PSearch

Opens the preview window. Type something and the window will update
automatically with all the search matches for the current file.

### PSearchw

As the `PSearch` command but uses the word under cursor for the search.
(Equal to the vim `*` mapping)


## Settings

### g:pse_max_height

With this setting you can set the maximum height for the window opened with 
the `PSearch` command.

default: 15


### g:pse_prompt

With this setting you can customize the look of the prompt used by the
`PSearch` command.

default: ' ❯ '


## Changelog

### v0.3

* Added jump-to-marks functionality for quick access to search results (thanks to Tobias Pflug).
* Minor bugfixes.

### v0.2

* Searches are now performed in all buffers. 
* Fix issues with some input characters.
* Add new controls for the PSearch window.

### v0.1

* First release
