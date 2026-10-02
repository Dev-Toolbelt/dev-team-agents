<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Files

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Manage Files**: [`Fileman::autocompletedir`](#fileman-autocompletedir), [`Fileman::copy_file`](#fileman-copy-file), [`Fileman::delete_file`](#fileman-delete-file), [`Fileman::empty_trash`](#fileman-empty-trash), [`Fileman::get_file_content`](#fileman-get-file-content), [`Fileman::get_file_information`](#fileman-get-file-information), [`Fileman::list_files`](#fileman-list-files), [`Fileman::move_file`](#fileman-move-file), [`Fileman::rename_file`](#fileman-rename-file), [`Fileman::restore_from_trash`](#fileman-restore-from-trash), [`Fileman::save_file_content`](#fileman-save-file-content), [`Fileman::transcode`](#fileman-transcode), [`Fileman::trash_file`](#fileman-trash-file), [`Fileman::upload_files`](#fileman-upload-files)
- **FTP Accounts**: [`Ftp::add_ftp`](#ftp-add-ftp), [`Ftp::delete_ftp`](#ftp-delete-ftp), [`Ftp::ftp_exists`](#ftp-ftp-exists), [`Ftp::get_quota`](#ftp-get-quota), [`Ftp::get_welcome_message`](#ftp-get-welcome-message), [`Ftp::list_ftp`](#ftp-list-ftp), [`Ftp::list_ftp_with_disk`](#ftp-list-ftp-with-disk), [`Ftp::passwd`](#ftp-passwd), [`Ftp::set_homedir`](#ftp-set-homedir), [`Ftp::set_quota`](#ftp-set-quota), [`Ftp::set_welcome_message`](#ftp-set-welcome-message)
- **FTP Server Settings**: [`Ftp::allows_anonymous_ftp`](#ftp-allows-anonymous-ftp), [`Ftp::allows_anonymous_ftp_incoming`](#ftp-allows-anonymous-ftp-incoming), [`Ftp::get_ftp_daemon_info`](#ftp-get-ftp-daemon-info), [`Ftp::get_port`](#ftp-get-port), [`Ftp::kill_session`](#ftp-kill-session), [`Ftp::list_sessions`](#ftp-list-sessions), [`Ftp::server_name`](#ftp-server-name), [`Ftp::set_anonymous_ftp`](#ftp-set-anonymous-ftp), [`Ftp::set_anonymous_ftp_incoming`](#ftp-set-anonymous-ftp-incoming)
- **Image Tools**: [`ImageManager::convert_file`](#imagemanager-convert-file), [`ImageManager::create_thumbnails`](#imagemanager-create-thumbnails), [`ImageManager::get_dimensions`](#imagemanager-get-dimensions), [`ImageManager::resize_image`](#imagemanager-resize-image)
- **WebDisk Settings**: [`WebDisk::delete_user`](#webdisk-delete-user), [`WebDisk::set_homedir`](#webdisk-set-homedir), [`WebDisk::set_password`](#webdisk-set-password), [`WebDisk::set_permissions`](#webdisk-set-permissions)

## Manage Files

<a id="fileman-autocompletedir"></a>
### `Fileman::autocompletedir` — Return autocomplete file and directory names

`GET /execute/Fileman/autocompletedir` · RO · since cPanel 54

This function returns any files and directories that begin with a specified string. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `path` · **required** · string · e.g. `public` — The prefix of the paths to complete.
- `dirsonly` · optional · integer (`1`, `0`) · default `0` — Whether to include only directories in the output.; `1` — **Only** include directories.; `0` — Include directories **and** files.
- `html` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to return HTML-encoded results.; `1` — Return HTML-encoded output.; `0` — Return plaintext output.
- `list_all` · optional · integer (`1`, `0`) · default `1` — Whether to return all files and directories inside the specified directory. If you set this parameter's value to `1`, you **must** set the `path` parameter's value to a full directory path.; `1` — Return **all** files and directories inside the specified directory.; `0` — Return partial file and directory name matches.

**Returns** `data`: array of object — An array of objects containing the files and directories that match the specified path.

- *(array of objects)*
  - `file` (string) — A file or directory that matches the specified path.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  autocompletedir \
  path='public'
```

<a id="fileman-copy-file"></a>
### `Fileman::copy_file` — Copy a file

`GET /execute/Fileman/copy_file` · RW · rollback: none · since cPanel 136

This function copies a file or directory to a new location and preserves the source permissions and modification time. If the destination is an existing directory, the source is copied into it. The function returns an error if the destination already exists. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `destination` · **required** · string <path> · e.g. `public_html/backup/file.txt` — The path to copy the source to.
- `source` · **required** · string <path> · e.g. `public_html/file.txt` — The path to the file or directory to copy.

**Returns** `data`: object

- `src` (string <path>) — The resolved source path.
- `dest` (string <path>) — The resolved destination path.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  copy_file \
  source='public_html/file.txt' \
  destination='public_html/backup/file.txt'
```

<a id="fileman-delete-file"></a>
### `Fileman::delete_file` — Delete a file permanently

`GET /execute/Fileman/delete_file` · RW · rollback: none · since cPanel 136

This function permanently removes a file or directory. The function removes directories recursively. This action cannot be undone; to remove a file reversibly, use the trash_file function instead. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `path` · **required** · string <path> · e.g. `public_html/unwanted.txt` — The path to the file or directory to delete.

**Returns** `data`: object

- `path` (string <path>) — The resolved path that the function deleted.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  delete_file \
  path='public_html/unwanted.txt'
```

<a id="fileman-empty-trash"></a>
### `Fileman::empty_trash` — Delete .trash folder content

`GET /execute/Fileman/empty_trash` · RW · rollback: none · since cPanel 60

This function purges content from the `.trash` folder in the user's home directory. Important: When you disable the [FileStorage role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `older_than` · optional · integer · default `0` · e.g. `31` — The maximum age in days of content that the function will not purge. Note: A value of `0` will purge everything from the user's `.trash` folder.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  empty_trash
```

<a id="fileman-get-file-content"></a>
### `Fileman::get_file_content` — Return file content

`GET /execute/Fileman/get_file_content` · RO · since cPanel 11.44

This function retrieves a file's content. Important: When you disable the [File Storage](https://go.cpanel.net/serverroles) role, the system **disables** this function. Note: JSON strings **must** be valid UTF-8. To retrieve a non-UTF-8 file via JSON, we recommend that you give `ISO-8859-1` as `from_charset` and `UTF-8` as `to_charset`, then decode the return payload’s `content` as UTF-8.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/user/public.html` — The file path to the directory that contains the selected file.
- `file` · **required** · string · e.g. `example.html` — The file to retrieve.
- `from_charset` · optional · string · default `_DETECT_` · e.g. `_DETECT_` — The file’s character encoding. This parameter defaults to `_DETECT_`, which indicates a request to detect the file’s character encoding.
- `to_charset` · optional · string · default `_LOCALE_` · e.g. `_LOCALE_` — The output character encoding. This parameter defaults to `_LOCALE_`, which indicates a request to use the session locale’s character encoding. Important: Contexts that serialize the API response as JSON **require** this value to be `utf-8` or `US-ASCII`. Behavior is **undefined** if the request indicates any other encoding.
- `update_html_document_encoding` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to update the file's HTML document encoding.; `1` — Update the file's HTML document encoding.; `0` — Don't update the file's HTML encoding.

**Returns** `data`: object

- `content` (string <binary>) — The file's contents.
- `dir` (string <path>) — The absolute path to the directory that contains the selected file.
- `filename` (string) — The file's name.
- `from_char` (string) — The file's previous character encoding.
- `from_charset` (any) — 
- `path` (string <path>) — The absolute path to the file.
- `to_char` (string) — The file's new character encoding.
- `to_charset` (any) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  get_file_content \
  dir='/home/user/public_html' \
  file='example.html'
```

<a id="fileman-get-file-information"></a>
### `Fileman::get_file_information` — Return file or directory information

`GET /execute/Fileman/get_file_information` · RO · since cPanel 11.44

This function returns the information for a specified file or directory. Important: When you disable the [File Storage](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `path` · **required** · string <path> · e.g. `public_html` — The directory from which to list files.
- `check_for_leaf_directories` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to flag directories that contain subdirectories.; `1` - Flag directories that contain subdirectories.; `0` - Do **not** flag directories that contain subdirectories.
- `include_mime` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return the file's MIME type.; `1` - Return the file's MIME type.; `0` - Do **not** return the file's MIME type.
- `include_permissions` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to parse the file owner's read and write permissions.; `1` - Parse the file owner's read and write permissions.; `0` - Do **not** parse the file owner's read and write permissions.
- `show_hidden` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include hidden files in the output.; `1` - Include hidden files.; `0` - Do **not** include hidden files.

**Returns** `data`: object

- `absdir` (string <path>) — The path to the user's home directory.
- `ctime` (integer <unix_timestamp>) — The file's creation time, Unix time format.
- `exists` (integer (`0`, `1`)) — Whether the file exists in the directory.; `1` - Exists.; `0` - Does **not** exist.
- `file` (string) — The filename.
- `fullpath` (string <path>) — The file's full filepath.
- `gid` (integer) — The file owner's system group ID.
- `humansize` (string) — The file's formatted size, followed by one of the following symbols: `KB` - kilobytes; `MB` - megabytes; `GB` - gigabytes
- `isleaf` (integer (`0`, `1`)) — Whether the directory contains subdirectories.; `1` - Contains subdirectories.; `0` - Does **not** contain subdirectories.
- `mimename` (string) — The file's MIME name.
- `mimetype` (string <MIME>) — The file's MIME type.
- `mode` (string) — The file's textual permissions in [Unix format](https://en.wikipedia.org/wiki/File-system_permissions#Notation_of_traditional_Unix_permissions).
- `mtime` (integer <unix_timestamp>) — The file's last modification time, in Unix time format.
- `nicemode` (integer) — The file's numerical permissions in [octal notation](https://en.wikipedia.org/wiki/File-system_permissions#Notation_of_traditional_Unix_permissions).
- `path` (string <path>) — The file's path.
- `rawmimename` (string <MIME>) — The file's raw MIME name.
- `rawmimetype` (string <MIME>) — The file's raw MIME type.
- `read` (integer (`0`, `1`)) — Whether the file is readable.
- `size` (integer) — The file's size, in bytes.
- `type` (string (`file`, `dir`, `char`, `block`, `fifo`, `link`, `socket`)) — The item's type.; `file` - File.; `dir` - Directory.; `char` - Character special device.; `block` - Block special device.; `fifo` - Named pipe.; `link` - Symbolic link.; `socket` - Unix domain socket.
- `uid` (integer) — The file owner's system user ID.
- `write` (integer (`0`, `1`)) — Whether the file is writable.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  get_file_information \
  path='public_html'
```

<a id="fileman-list-files"></a>
### `Fileman::list_files` — Return directory content

`GET /execute/Fileman/list_files` · RO · since cPanel 11.44

This function returns a sorted list of files and directories. Important: When you disable the [FileStorage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function. For more information, read our How to Use Server Profiles documentation.

**Parameters**

- `dir` · **required** · string · e.g. `public_html` — The directory from which to list files.
- `check_for_leaf_directories` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return directories that contain subdirectories.; `1` — Return subdirectories.; `0` — Do **not** retain subdirectories.
- `include_mime` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return the file's MIME type.; `1` — Include MIME type.; `0` — Do **not** include MIME type. Note: If you set this value to `0` but also include the `mime_types` or `raw_mime_types` parameters, the function **overrides** your specified value and sets this parameter to `1`.
- `include_permissions` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to parse the file owner's read and write permissions.; `1` — Parse file permissions.; `0` — Do **not** parse file permissions.
- `limit_to_list` · optional · integer (`0`, `1`) · e.g. `0` — Whether to return only entries that begin with the `filepath-` prefix.; `1` — Return only files that begin with the `filepath-` prefix.; `0` — Return **all** files. If you do not use this parameter, the function returns all filenames.
- `mime_types` · optional · string · e.g. `text-plain` — The MIME types to return.; If you use this parameter, the function returns the specified MIME types and sets the `include_mime` parameter's value to `1`.; If you do **not** use this parameter, the function returns all MIME types.
- `only_these_files` · optional · string · e.g. `cpbackup-exclude.conf` — A comma-separated list of files to return. If you do not use this parameter, the function returns all files.
- `raw_mime_types` · optional · string · e.g. `text/plain` — The raw MIME types to return.; If you use this parameter, the function returns the specified MIME types and sets the `include_mime` parameter's value to `1`.; If you do **not** use this parameter, the function returns all MIME types.
- `show_hidden` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include hidden files in the output.; `1` — Include hidden files.; `0` — Do **not** include hidden files.
- `types` · optional · array of string — A pipe-separated list of file types to return.; `file` — A file.; `dir` — A directory.; `char` — A character special device.; `block` — A block special device.; `fifo` — A named pipe (FIFO).; `link` — A symbolic link.; `socket` — A Unix domain socket. If you do not use this parameter, the function returns all file types.

**Returns** `data`: object

- `dirs` (array of object) — An array of objects containing information about each directory.
  - *(array of objects)*
    - `absdir` (string <path>) — The file path to the user's home directory.
    - `ctime` (integer <unix_timestamp>) — The directory's creation date.
    - `exists` (integer (`0`, `1`)) — Whether the directory exists in the directory.; `1` — Exists.; `0` — Does **not** exist.
    - `file` (string) — The directory name.
    - `fullpath` (string <path>) — The directory's full directory path.
    - `gid` (integer) — The directory owner's system group ID.
    - `humansize` (string) — The formatted size of the directory.
    - `isleaf` (integer (`0`, `1`)) — Whether the directory contains subdirectories.; `1` — Contains subdirectories.; `0` — Does **not** contain subdirectories.
    - `isparent` (integer (`0`, `1`)) — Whether the directory is a parent record.; `1` — A parent record.; `0` — **Not** a parent record.
    - `mimename` (string) — The MIME type's name.
    - `mimetype` (string) — The directory's MIME's type.
    - `mode` (string <unix-file-permission>) — The directory's textual permissions in [Unix format](http://en.wikipedia.org/wiki/File_system_permissions#Notation_of_traditional_Unix_permissions).
    - `mtime` (integer <unix_timestamp>) — The directory's last modification time.
    - `nicemode` (integer <unix-file-permission>) — The directory's numerical permissions.
    - `path` (string <path>) — The path to the directory.
    - `rawmimename` (string) — The directory's raw MIME type's name.
    - `rawmimetype` (string) — The directory's raw MIME type.
    - `read` (integer (`0`, `1`)) — Whether the directory is readable.; `1` — Readable.; `0` — **Not** readable.
    - `size` (integer) — The directory's size, in bytes.
    - `type` (string (`file`, `dir`, `char`, `block`, `fifo`, `link`, `socket`)) — The item's type.; `file` — A file.; `dir` — A directory.; `char` — A character special device.; `block` — A block special device.; `fifo` - A named pipe (FIFO).; `link` — A symbolic link.; `socket` — A Unix domain socket
    - `uid` (integer) — The directory owner's system user ID.
    - `write` (integer (`0`, `1`)) — Whether the directory is writable.; `1` — Writable.; `0` — **Not** writable.
- `files` (array of object) — An array of objects containing information about each file.
  - *(array of objects)*
    - `absdir` (string <path>) — The file path to the user's home directory.
    - `ctime` (integer <unix_timestamp>) — The file's creation time.
    - `exists` (integer (`0`, `1`)) — Whether the file exists in the directory.; `1` — Exists.; `0` — Does **not** exist.
    - `file` (string) — The filename.
    - `fullpath` (string <path>) — The file's full file path.
    - `gid` (integer) — The file owner's system group ID.
    - `humansize` (string) — The formatted size of the file.
    - `isleaf` (integer (`0`, `1`)) — Whether the directory contains subdirectories.; `1` — Contains subdirectories.; `0` — Does **not** contain subdirectories.
    - `isparent` (integer (`0`, `1`)) — Whether the file is a parent record.; `1` — A parent record.; `0` — **Not** a parent record.
    - `mimename` (string) — The file's MIME type name.
    - `mimetype` (string) — The file's MIME type.
    - `mode` (string <unix-file-permission>) — The file's textual permissions.
    - `mtime` (integer <unix_timestamp>) — The file's last modification time.
    - `nicemode` (integer <unix-file-permission>) — The file's numerical permissions.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  list_files \
  dir='public_html'
```

<a id="fileman-move-file"></a>
### `Fileman::move_file` — Move a file

`GET /execute/Fileman/move_file` · RW · rollback: none · since cPanel 136

This function moves a file or directory to a new location. If the destination is an existing directory, the source is moved into it. The function returns an error if the destination already exists. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `destination` · **required** · string <path> · e.g. `public_html/subdir/new.txt` — The path to move the source to.
- `source` · **required** · string <path> · e.g. `public_html/old.txt` — The path to the file or directory to move.

**Returns** `data`: object

- `src` (string <path>) — The resolved source path.
- `dest` (string <path>) — The resolved destination path.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  move_file \
  source='public_html/old.txt' \
  destination='public_html/subdir/new.txt'
```

<a id="fileman-rename-file"></a>
### `Fileman::rename_file` — Rename a file

`GET /execute/Fileman/rename_file` · RW · rollback: clean · since cPanel 136

This function changes the name of a file or directory within the same directory. To move a file to a different directory, use the move_file function. The function returns an error if the destination already exists. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `destination` · **required** · string <path> · e.g. `public_html/new.txt` — The new path, in the same directory as the source.
- `source` · **required** · string <path> · e.g. `public_html/old.txt` — The path to the file or directory to rename.

**Returns** `data`: object

- `src` (string <path>) — The resolved source path.
- `dest` (string <path>) — The resolved destination path.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  rename_file \
  source='public_html/old.txt' \
  destination='public_html/new.txt'
```

<a id="fileman-restore-from-trash"></a>
### `Fileman::restore_from_trash` — Restore a file from the trash

`GET /execute/Fileman/restore_from_trash` · RW · rollback: none · since cPanel 136

This function restores a previously trashed file or directory to its original location. Pass the item's original path. If the path was trashed more than once, the function restores the most recent copy. The function returns an error if the original path already exists. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `path` · **required** · string <path> · e.g. `public_html/unwanted.txt` — The original path of the trashed file or directory.

**Returns** `data`: object

- `path` (string <path>) — The restored path.
- `trash_leaf` (string) — The trash directory name that the function restored from.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  restore_from_trash \
  path='public_html/unwanted.txt'
```

<a id="fileman-save-file-content"></a>
### `Fileman::save_file_content` — Save file

`GET /execute/Fileman/save_file_content` · RW · rollback: none · since cPanel 11.44

This function saves a file in a directory and encodes it in a character set. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `file` · **required** · string · e.g. `example.html` — The files to retrieve.
- `content` · optional · string · e.g. `hi` — The new file's contents. If you do **not** use this parameter, the function creates a blank file.
- `dir` · optional · string <path> · e.g. `/home/username/public_html` — The directory that contains the selected file. Note: This parameter defaults to the currently-authenticated user's `/home` directory.
- `fallback` · optional · integer (`0`, `1`) · default `1` · e.g. `0` — Whether the function will return an error or save in the default character set if it cannot save in the specified character set.; `1` — Save in the default character set.; `0` — Return an error.
- `from_charset` · optional · string · default `UTF-8` · e.g. `UTF-8` — The [character set encoding](https://en.wikipedia.org/wiki/Character_encoding) of the `content` parameter's value.
- `to_charset` · optional · string · default `UTF-8` · e.g. `ASCII` — The [character set encoding](https://en.wikipedia.org/wiki/Character_encoding) in which to encode the file.

**Returns** `data`: object

- `from_charset` (string) — The file's character set.
- `path` (string <path>) — The path to the file.
- `to_charset` (string) — The file's new character set.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  save_file_content \
  file='example.html'
```

<a id="fileman-transcode"></a>
### `Fileman::transcode` — Update buffer encoding

`GET /execute/Fileman/transcode` · RW · rollback: none · since cPanel 11.44

This function converts a buffer from one encoding language to another. Important: When you disable the [File Storage role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `content` · **required** · string · e.g. `hi` — The file's contents.
- `discard_illegal` · optional · integer (`0`, `1`) · e.g. `1` — Whether to discard any characters that do not transcode correctly.; `1` - Discard invalid characters.; `0` - Transcode invalid characters in the default [character set encoding](https://en.wikipedia.org/wiki/Character_encoding).
- `from_charset` · optional · string · e.g. `UTF-8` — The file's current [character set encoding](https://en.wikipedia.org/wiki/Character_encoding).
- `to_charset` · optional · string · e.g. `ASCII` — The [character set encoding](https://en.wikipedia.org/wiki/Character_encoding) in which to encode the file.
- `transliterate` · optional · integer (`0`, `1`) · e.g. `0` — Whether to transcode invalid characters to valid characters in the new character set encoding.; `1` - Transcode invalid characters in the new [character set encoding](https://en.wikipedia.org/wiki/Character_encoding).; `0` - Return an error message.

**Returns** `data`: object

- `charset` (string) — The file's new character set.
- `content` (string) — The file's content.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  transcode \
  content='hi'
```

<a id="fileman-trash-file"></a>
### `Fileman::trash_file` — Move a file to the trash

`GET /execute/Fileman/trash_file` · RW · rollback: none · since cPanel 136

This function moves a file or directory to the account trash directory and records its original path so that you can restore it later with the restore_from_trash function. Important: When you disable the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `path` · **required** · string <path> · e.g. `public_html/unwanted.txt` — The path to the file or directory to move to the trash.

**Returns** `data`: object

- `path` (string <path>) — The resolved original path.
- `trash_leaf` (string) — The name of the item inside the trash directory.

```bash
uapi --output=jsonpretty \
  --user=username \
  Fileman \
  trash_file \
  path='public_html/unwanted.txt'
```

<a id="fileman-upload-files"></a>
### `Fileman::upload_files` — Upload files

`POST /execute/Fileman/upload_files` · RW · rollback: none · since cPanel 11.44 · CLI support: False

This function uploads one or more files to a directory. Important:  You **must** send the files as parts of a `multipart/form-data` request body. Query parameters cannot carry a file. For security reasons, the system discards any query parameter whose name begins with `file-`.; You can't pass the file parts on the command line, and LiveAPI can't call this function at all, because neither can send a `multipart/form-data` body.; When you disable the [File Storage](https://go.cpanel.net/serverroles) role, the system **disables** this function.; You cannot call this function through WHM API 1's [uapi_cpanel](https://go.cpanel.net/UseWHMAPItoCallcPanelAPIandUAPI) function. Note:  The system names each stored file after that part's `filename` attribute, **not** after the form field's name. By convention, name the fields `file-0`, `file-1`, and so on, as the cPanel interface does.; The system scans every uploaded file for viruses and rejects an infected file.; The system rejects a filename of `.` or `..`, or a filename that contains control characters or any of the `<`, `>`, `;`, and `/` characters.; If one request contains two files with the same name, the system renames the second file. For example, `example-2.png`.; For more information about how to use this function in your custom code, read our [Use UAPI's `Fileman::upload_files` Function in Custom Code tutorial](https://go.cpanel.net/tutorial-use-uapis-fileman-upload-files-function-in-custom-code).

**Parameters**

- `dir` · optional · string <path> · e.g. `/home/username/public_html` — The directory in which to store the uploaded files. Note:  A relative path resolves against the account's home directory.; This parameter defaults to the account's home directory.; The system creates the directory if it does not exist.
- `get_disk_info` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include the account's disk usage in the response.; `1` - Return the `diskinfo` object.; `0` - Do not return the `diskinfo` object.
- `overwrite` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to replace a file that already exists in the target directory.; `1` - Overwrite the existing file.; `0` - Fail that file with an "already exists" reason.
- `permissions` · optional · string <unix-file-permission> · default `0644` · e.g. `0600` — The permissions to apply to every file in the request, in octal notation. Note:  The system reads both `0644` and `644` as octal.; This parameter defaults to `0644`.; If the system cannot apply the permissions, the upload still succeeds and the function returns a warning for that file.

**Request body** (`multipart/form-data`)

- `file-0` (string <binary>) — A file to upload.

**Returns** `data`: object

- `diskinfo` (object) — The account's disk usage and upload limits.
  - `file_upload_max_bytes` (string) — The largest size, in bytes, that a single uploaded file may reach.
  - `file_upload_must_leave_bytes` (string) — The amount of free space, in bytes, that must remain after an upload.
  - `file_upload_remain` (string) — The total size, in bytes, that the account may upload now.
  - `fileslimit` (integer or string) — The number of inodes that the account may use.
  - `filesremain` (integer or string) — The number of inodes that the account may still use.
  - `filesused` (integer or string) — The number of inodes that the account uses.
  - `spacelimit` (string) — The disk space, in bytes, that the account may use.
  - `spaceremain` (string) — The disk space, in bytes, that the account may still use.
  - `spaceused` (string) — The disk space, in bytes, that the account uses.
- `failed` (integer) — The number of files that the system did not store.
- `succeeded` (integer) — The number of files that the system stored.
- `uploads` (array of object) — One entry for each file in the request.
  - *(array of objects)*
    - `file` (string) — The file's name.
    - `reason` (string) — A description of the outcome for this file.
    - `size` (integer) — The stored file's size, in bytes.
    - `status` (integer (`0`, `1`)) — * `1` - The system stored the file.; `0` - The upload failed.
    - `warnings` (array of string) — Non-critical problems, such as a failure to apply the file's ownership or permissions.
- `warned` (integer) — The number of files that produced warnings.

## FTP Accounts

<a id="ftp-add-ftp"></a>
### `Ftp::add_ftp` — Create FTP account

`GET /execute/Ftp/add_ftp` · RW · rollback: none · since cPanel 11.42

This function creates an FTP account. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `user` · **required** · string · e.g. `username` — The new FTP account username.
- `disallowdot` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to strip dots (`.`) from the username.; `1` — Strip dots.; `0` — Do **not** strip dots.
- `domain` · optional · string <domain> · e.g. `example.com` — The FTP user's associated domain. This must be a domain that the cPanel account owns. Note: This parameter defaults to the cPanel account's primary domain.
- `homedir` · optional · string <path> · e.g. `exampleftp` — The path to the FTP account's root directory, relative to the cPanel account's home directory. If you don't set this, it defaults to a directory with the same name as the FTP account.
- `pass` · optional · string · e.g. `123456luggage` — The new FTP account password. Note: You can use the `pass_hash` parameter in place of this parameter. However, you **cannot** use both the `pass` and `pass_hash` parameters in the same request.
- `pass_hash` · optional · string · default `` — The account's password hash. Note:  You can use this parameter in place of the `pass` parameter. However, you **cannot** use both the `pass` and `pass_hash` parameters in the same request.; You can find your server's password hash type in the `/etc/sysconfig/authconfig` file.
- `quota` · optional · integer · default `0` · e.g. `42` — The FTP account's maximum disk usage quota, in megabytes (MB). Note: A value of `0` grants the FTP account unlimited disk space.

**Returns** `data`: object (`None`)

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  add_ftp \
  user='username2' \
  pass='123456luggage'
```

<a id="ftp-delete-ftp"></a>
### `Ftp::delete_ftp` — Delete FTP account

`GET /execute/Ftp/delete_ftp` · RW · rollback: none · since cPanel 11.42

This function deletes an FTP account. Important: When you disable the [*FTP* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `user` · **required** · string · e.g. `username` — The FTP account's username.
- `destroy` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to delete the FTP account's home directory.; `1` — Delete the home directory.; `0` — Do **not** delete the home directory.
- `domain` · optional · string <domain> · e.g. `example.com` — The user's associated domain. Note: This parameter defaults to the cPanel account's primary domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  delete_ftp \
  user='username2'
```

<a id="ftp-ftp-exists"></a>
### `Ftp::ftp_exists` — Return whether an FTP account exists

`GET /execute/Ftp/ftp_exists` · RO · since cPanel 11.42

This function checks whether an FTP account exists. Note: This function returns only metadata if the FTP account exists, or an error if the FTP account does **not** exist.

**Parameters**

- `user` · **required** · string · e.g. `us_chickens` — The FTP account's username.
- `domain` · optional · string <domain> · e.g. `example.com` — The user's associated domain. Note: This parameter defaults to the cPanel account's primary domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  ftp_exists \
  user='us_chickens'
```

<a id="ftp-get-quota"></a>
### `Ftp::get_quota` — Return FTP account's quota

`GET /execute/Ftp/get_quota` · RO · since cPanel 11.42

This function checks an FTP account's quota. Important: When you disable the [_FTP role_](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · **required** · string · e.g. `user1` — The FTP account's username.
- `domain` · optional · string <domain> · e.g. `example.com` — The user's associated domain. Note: This parameter defaults to the cPanel account's primary domain.

**Returns** `data`: string — The FTP account's quota.; `unlimited`; A positive integer that represents the maximum amount of disk space that the FTP account can use, in megabytes (MB).

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  get_quota \
  account='user1'
```

<a id="ftp-get-welcome-message"></a>
### `Ftp::get_welcome_message` — Return FTP account's welcome message

`GET /execute/Ftp/get_welcome_message` · RO · since cPanel 11.42

This function retrieves the cPanel account's FTP welcome message. Important: When you disable the [*FTP* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: string — The cPanel account's FTP welcome message.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  get_welcome_message
```

<a id="ftp-list-ftp"></a>
### `Ftp::list_ftp` — Return FTP accounts

`GET /execute/Ftp/list_ftp` · RO · since cPanel 11.42

This function lists FTP account information. Important: When you disable the [*FTP* role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function. For more information, read our How to Use Server Profiles documentation.

**Parameters**

- `include_acct_types` · optional · string · e.g. `main|anonymous` — A list of the FTP account types to include in the function's results.; `anonymous`; `logaccess`; `main`; `sub` If you do not specify this parameter, this function returns all FTP account types. Note:  Separate multiple types with the pipe character (`\|`).; In browser-based calls, use `%7C`.
- `skip_acct_types` · optional · string · e.g. `main|anonymous` — A list of the FTP account types to exclude from the function's results.; `anonymous`; `logaccess`; `main`; `sub` If you do not specify this parameter, this function does **not** exclude any account types. Note:  Separate multiple types with the pipe character (`\|`).; In browser-based calls, use `%7C`.

**Returns** `data`: array of object

- *(array of objects)*
  - `homedir` (string <path>) — The absolute path to the FTP account's document root.
  - `type` (string (`anonymous`, `logaccess`, `main`, `sub`)) — The type of FTP account.; `anonymous`; `logaccess`; `main`; `sub`
  - `user` (string) — The username for an FTP account on the cPanel account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  list_ftp
```

<a id="ftp-list-ftp-with-disk"></a>
### `Ftp::list_ftp_with_disk` — Return FTP accounts and disk usage

`GET /execute/Ftp/list_ftp_with_disk` · RO · since cPanel 11.42

This function lists FTP account and disk usage information. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `include_acct_types` · optional · string · e.g. `main|anonymous` — A pipe-delimited list of the FTP account types to include in the function's results. If you do not specify this parameter, the function returns all FTP account types. Valid types for this list are: `anonymous`; `logaccess`; `main`; `sub`
- `skip_acct_types` · optional · string · e.g. `main|anonymous` — A pipe-delimited list of the FTP account types to exclude from the function's results. If you do not specify this parameter, the function does **not** exclude any account types. Valid types for this list are: `anonymous`; `logaccess`; `main`; `sub`

**Returns** `data`: array of object

- *(array of objects)*
  - `_diskquota` (string <^\d+\.\d+$>) — The FTP account's quota in megabytes, with two digits of fractional precision, encoded as a string.
  - `_diskused` (string <^\d+\.\d+$>) — The amount of disk space in megabytes that the account currently uses, with two digits of fractional precision, encoded as a string.
  - `accttype` (string (`anonymous`, `logaccess`, `main`, `sub`)) — The type of FTP account.; `anonymous`; `logaccess`; `main`; `sub`
  - `deleteable` (integer (`0`, `1`)) — Whether the function's caller can delete the account.; `1` – The caller can delete the account.; `0` – The caller **cannot** delete the account.
  - `dir` (string) — The absolute path to the FTP account's document root.
  - `diskquota` (string (`unlimited`) or string <^\d+\.\d+$>) — The FTP account's quota.; `unlimited`; The disk quota in megabytes, with two digits of fractional precision, encoded as a string.
  - `diskused` (string <^\d+\.\d+$>) — The amount of disk space in megabytes that the account currently uses, with two digits of fractional precision, encoded as a string.
  - `diskusedpercent` (integer) — The percentage of the disk space quota that the account currently uses.
  - `diskusedpercent20` (integer) — The percentage of disk space that the account currently uses, rounded in 20 percent increments.
  - `htmldir` (string) — The path to the FTP account's HTML directory.
  - `humandiskquota` (string) — The FTP account's quota, in human-readable format.; `None` — The function returns this value if the account has an unlimited quota.; The quota in megabytes (MB), a space, and the characters `MB`.
  - `humandiskused` (string) — The amount of disk space that the account currently uses, in human-readable format.
  - `login` (string) — The FTP account username.
  - `reldir` (string) — The path to the FTP account's document root, relative to the cPanel account's home directory.
  - `serverlogin` (string) — The full FTP login username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  list_ftp_with_disk
```

<a id="ftp-passwd"></a>
### `Ftp::passwd` — Update FTP account's password

`GET /execute/Ftp/passwd` · RW · rollback: none · since cPanel 11.42

This function changes an FTP account's password. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `pass` · **required** · string · e.g. `12345luggage` — The FTP account's new password.
- `user` · **required** · string · e.g. `ftpaccount` — The FTP account username.
- `domain` · optional · string · e.g. `example.com` — The user's associated domain. Note: This parameter defaults to the cPanel account's primary domain

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  passwd \
  user='ftpaccount' \
  pass='123456luggage'
```

<a id="ftp-set-homedir"></a>
### `Ftp::set_homedir` — Update FTP account's home directory

`GET /execute/Ftp/set_homedir` · RW · rollback: none · since cPanel 54

This function changes the home directory for FTP accounts. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `user` · **required** · string · e.g. `example1` — The FTP account username.
- `domain` · optional · string <domain> · e.g. `example.com` — The user's associated domain. Note: The default value is the cPanel account's primary domain.
- `homedir` · optional · string <path> · default `user@domain/` · e.g. `example1/` — The FTP account's home directory Note: This parameter defaults to the `user@domain` subdirectory in the cPanel account's home directory with the name, where user and domain represent the `user` and `domain` parameters.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  set_homedir \
  user='example1'
```

<a id="ftp-set-quota"></a>
### `Ftp::set_quota` — Update FTP account's quota

`GET /execute/Ftp/set_quota` · RW · rollback: none · since cPanel 11.42

This function changes an FTP account's quota. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `user` · **required** · string · e.g. `ftpaccount` — The FTP account username.
- `domain` · optional · string <domain> · e.g. `example.com` — The user's associated domain. Note: The default value is the cPanel account's primary domain.
- `kill` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to disable quotas for the FTP account.; `1` - Disable quotas.; `0` - Enable quotas. Note: If you disable quotas for an FTP account, you grant that account unlimited disk space.
- `quota` · optional · integer · default `0` · e.g. `500` — The new quota, in megabytes. Note: Setting this parameter to `0` grants the account unlimited disk space.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  set_quota \
  user='ftpaccount'
```

<a id="ftp-set-welcome-message"></a>
### `Ftp::set_welcome_message` — Update FTP welcome message

`GET /execute/Ftp/set_welcome_message` · RW · rollback: none · since cPanel 11.42

This function sets the FTP welcome message. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `message` · **required** · string · e.g. `Greetings, Professor Falken.` — The cPanel account's new FTP welcome message.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  set_welcome_message \
  message='Greetings, Professor Falken.'
```

## FTP Server Settings

<a id="ftp-allows-anonymous-ftp"></a>
### `Ftp::allows_anonymous_ftp` — Return if anonymous FTP connections allowed

`GET /execute/Ftp/allows_anonymous_ftp` · RO · since cPanel 11.42

This function checks whether the account allows anonymous FTP connections. Important: When you disable the [*FTP* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `allows` (integer (`0`, `1`)) — Whether the cPanel account allows anonymous FTP connections.; `1` - Allowed.; `0` - **Not** allowed.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  allows_anonymous_ftp
```

<a id="ftp-allows-anonymous-ftp-incoming"></a>
### `Ftp::allows_anonymous_ftp_incoming` — Return if anonymous FTP transfers allowed

`GET /execute/Ftp/allows_anonymous_ftp_incoming` · RO · since cPanel 11.42

This function checks whether the account allows inbound anonymous FTP transfers. Important: When you disable the [*FTP* role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: object

- `allows` (integer (`0`, `1`)) — Whether the cPanel account allows inbound anonymous FTP transfers.; `1` - Allowed.; `0` - Not allowed.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  allows_anonymous_ftp_incoming
```

<a id="ftp-get-ftp-daemon-info"></a>
### `Ftp::get_ftp_daemon_info` — Return FTP server's information

`GET /execute/Ftp/get_ftp_daemon_info` · RO · since cPanel 54

This function retrieves the extended information about the server's FTP daemon.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether the server's FTP daemon is enabled.; `1` – Enabled.; `0` – Disabled.
- `name` (string (`pure-ftpd`, `proftpd`, ``)) — The FTP server's name.; `pure-ftpd`; `proftpd`; An empty string.
- `supports` (object) — This object contains the features that the FTP daemon supports.
  - `login_without_domain` (integer (`0`, `1`)) — Whether the FTP daemon supports username authentication without the user's domain.; `1` – Supported.; `0` – **Not** supported.
  - `quota` (integer (`0`, `1`)) — Whether the FTP daemon supports disk quotas.; `1` – Supported.; `0` – **Not** supported.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  get_ftp_daemon_info
```

<a id="ftp-get-port"></a>
### `Ftp::get_port` — Return FTP server's port

`GET /execute/Ftp/get_port` · RO · since cPanel 11.42

This function returns the FTP port. Important: When you disable the [*FTP* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `port` (integer) — The FTP port.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  get_port
```

<a id="ftp-kill-session"></a>
### `Ftp::kill_session` — Stop FTP session

`GET /execute/Ftp/kill_session` · RW · rollback: none · since cPanel 11.42

This function kills FTP sessions. Important: When you disable the [*FTP* Role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `login` · optional · string · default `all` · e.g. `weeones` — The username for the session's FTP account. Note: To stop all FTP sessions for the cPanel account, set this parameter to the `all` value.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  kill_session
```

<a id="ftp-list-sessions"></a>
### `Ftp::list_sessions` — Return FTP server's active sessions

`GET /execute/Ftp/list_sessions` · RO · since cPanel 11.42

This function lists the FTP server's active sessions. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `cmdline` (string) — Information about the FTP process, from the `ps` ([process status](http://www.linfo.org/ps.html)) command.
  - `file` (string) — The file that the session is processing.
  - `host` (string <domain> or string <ipv4>) — The IP address or hostname that connected to the FTP server.
  - `login` (string) — The FTP session login time.
  - `pid` (integer) — The session's PID.
  - `status` (string (`IDLE`, `DL`, `UL`)) — The session's status.; `IDLE` - The session is connected, but idle.; `DL` - A download is in progress.; `UL` - An upload is in progress.
  - `user` (string) — The FTP account username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  list_sessions
```

<a id="ftp-server-name"></a>
### `Ftp::server_name` — Return whether server uses ProFTPD or Pure-FTPd

`GET /execute/Ftp/server_name` · RO · since cPanel 11.42

This function checks whether the server uses ProFTPD or Pure-FTPd. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: string (`pure-ftpd`, `proftpd`, `disabled`) — The FTP server.; `pure-ftpd` - The Pure-FTPD server.; `proftpd` - The ProFTPD FTP server.; `disabled` - FTP has been disabled on this server.

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  server_name
```

<a id="ftp-set-anonymous-ftp"></a>
### `Ftp::set_anonymous_ftp` — Enable or disable anonymous FTP logins

`GET /execute/Ftp/set_anonymous_ftp` · RW · rollback: none · since cPanel 11.42

This function enables or disables anonymous FTP logins. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `set` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable or disable anonymous FTP logins.; `1` - Enable.; `0` - Disable.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  set_anonymous_ftp
```

<a id="ftp-set-anonymous-ftp-incoming"></a>
### `Ftp::set_anonymous_ftp_incoming` — Enable or disable anonymous incoming FTP transfers

`GET /execute/Ftp/set_anonymous_ftp_incoming` · RW · rollback: none · since cPanel 11.42

This function enables or disables inbound anonymous FTP transfers. Important: When you disable the [FTP role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `set` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable or disable inbound anonymous FTP transfers.; `1` - Enable.; `0` - Disable.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Ftp \
  set_anonymous_ftp_incoming
```

## Image Tools

<a id="imagemanager-convert-file"></a>
### `ImageManager::convert_file` — Create image with new format

`GET /execute/ImageManager/convert_file` · RW · rollback: none · since cPanel 82

This function converts an image to a new file format. Important: When you disable the [WebServer role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `image_file` · **required** · string · e.g. `images/myimage.jpg` — The image file to convert, relative to the cPanel account's `/home` directory.
- `type` · **required** · string · e.g. `png` — The format to which to convert the images.

**Returns** `data`: object

- `converted_file` (string) — The new absolute filepath to the image.

```bash
uapi --output=jsonpretty \
  --user=username \
  ImageManager \
  convert_file \
  image_file='images/myimage.jpg' \
  type='png'
```

<a id="imagemanager-create-thumbnails"></a>
### `ImageManager::create_thumbnails` — Create image thumbnails

`GET /execute/ImageManager/create_thumbnails` · RW · rollback: none · since cPanel 82

This function creates thumbnails from images. The function saves the new thumbnail images in a thumbnails subdirectory inside the original directory. The system prepends thumbnail filenames with ``tn_`` (for example, ``tn_picture.jpg``). Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `dir` · **required** · string · e.g. `images` — The path to the directory where the image resides. When you pass this parameter, the function creates a thumbnail directory directly below the image directory. **NOTE:** This parameter can use an absolute directory path or a path relative to the user's home directory.
- `height_percentage` · **required** · integer · e.g. `25` — The percentage by which to reduce the thumbnails' height.
- `width_percentage` · **required** · integer · e.g. `25` — The percentage by which to reduce the thumbnails' width.

**Returns** `data`: array of object — An array of objects containing thumbnail file information.

- *(array of objects)*
  - `failed` (integer (`1`)) — Whether the function failed to create the thumbnail file.
  - `file` (string) — The file from which the function generated the thumbnail file.
  - `reason` (string) — The reason that the function didn't create the thumbnail file.
  - `thumbnail_file` (string) — The thumbnail file that the function generated.

```bash
uapi --output=jsonpretty \
  --user=username \
  ImageManager \
  create_thumbnails \
  dir='images' \
  width_percentage='25' \
  height_percentage='25'
```

<a id="imagemanager-get-dimensions"></a>
### `ImageManager::get_dimensions` — Return image dimensions

`GET /execute/ImageManager/get_dimensions` · RO · since cPanel 82

This function returns the dimensions of the image file that you specify. Important: When you disable the [WebServer role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `image_file` · **required** · string · e.g. `image/myimage.jpg` — The path to the file to measure. Note: Use the absolute filepath or a path relative to the user's home directory.

**Returns** `data`: object

- `height` (integer) — The image's height, in pixels.
- `width` (integer) — The image's width, in pixels.

```bash
uapi --output=jsonpretty \
  --user=username \
  ImageManager \
  get_dimensions \
  image_file='image/myimage.jpg'
```

<a id="imagemanager-resize-image"></a>
### `ImageManager::resize_image` — Save resized image

`GET /execute/ImageManager/resize_image` · RW · rollback: clean · since cPanel 82

This function resizes a specified image. Important: When you disable the [WebServer role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `height` · **required** · integer · e.g. `300` — The height to which to set the image size.
- `image_file` · **required** · string · e.g. `/images/image.jpg` — The name of the file to scale. Note: Use the absolute filepath or a filepath relative to the user's home directory.
- `width` · **required** · integer · e.g. `200` — The width to which to set the image size.
- `save_original_as` · optional · string · e.g. `images/original.jpg` — The path to the directory in which to save a copy the original image file. Note:  If you don't pass this parameter, the function doesn't save a copy of the original image.; Use the absolute filepath or a filepath relative to the user's home directory.

**Returns** `data`: string — The absolute filepath to the resized image.

```bash
uapi --output=jsonpretty \
  --user=username \
  ImageManager \
  resize_image \
  image_file='images/image.jpg' \
  width='200' \
  height='300'
```

## WebDisk Settings

<a id="webdisk-delete-user"></a>
### `WebDisk::delete_user` — Delete Web Disk account

`GET /execute/WebDisk/delete_user` · RW · rollback: none · since cPanel 54

This function deletes a Web Disk account. Important: When you disable the [Web Disk role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `destroy` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to recursively delete the Web Disk account's folder and all of its contents.; `1` - Delete the folder for the Web Disk account; `0` - Do **not** delete the folder for the Web Disk account.
- `user` · **required** · string <email> · e.g. `example1@example.com` — The Web Disk account username.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  WebDisk \
  delete_user \
  user='example1@example.com' \
  destroy='1'
```

<a id="webdisk-set-homedir"></a>
### `WebDisk::set_homedir` — Update Web Disk home directory location

`GET /execute/WebDisk/set_homedir` · RW · rollback: none · since cPanel 54

This function changes the home directory for a Web Disk account. Important: When you disable the [Web Disk role](https://go.cpanel.net/serveroles), the system **disables** this function.

**Parameters**

- `homedir` · **required** · string <path> · e.g. `example1/` — The Web Disk account's home directory.
- `user` · **required** · string <email> · e.g. `example1@example.com` — The Web Disk account username.
- `private` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to set the Web Disk directory's permissions to public or private.; `1` - Private (`0700`); `0` - Public (`0755`)

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  WebDisk \
  set_homedir \
  user='example1@example.com' \
  homedir='example1/'
```

<a id="webdisk-set-password"></a>
### `WebDisk::set_password` — Update Web Disk account password

`GET /execute/WebDisk/set_password` · RW · rollback: clean · since cPanel 54

This function changes the Web Disk account's password. Important: When you disable the [Web Disk role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `password` · **required** · string · e.g. `123456luggage` — The Web Disk account's password.
- `user` · **required** · string <email> · e.g. `example1@example.com` — The Web Disk account username.
- `enabledigest` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable Digest Authentication.; `1` - Enable Digest Authentication.; `0` - Disable Digest Authentication.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  WebDisk \
  set_password \
  user='example1@example.com' \
  password='123456luggage'
```

<a id="webdisk-set-permissions"></a>
### `WebDisk::set_permissions` — Update Web Disk home directory permissions

`GET /execute/WebDisk/set_permissions` · RW · rollback: clean · since cPanel 54

This function changes the Web Disk home directory's permissions. Important: When you disable the [Web Disk role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `perms` · **required** · string (`ro`, `rw`) · e.g. `rw` — The Web Disk account's home directory file permissions.; `ro` — Read-only permissions.; `rw` — Read and write permissions.
- `user` · **required** · string <email> · e.g. `example1@example.com` — The Web Disk account's username.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  WebDisk \
  set_permissions \
  user='example1@example.com' \
  perms='rw'
```

