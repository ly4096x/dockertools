# dockertools
A small script that adds useful commands for docker

## Usage

`dockertools update-images`: Update all pulled images with respect to their tags.

`dockertools remove-none-images`: Remove all `<none>` tagged images if they are not being used by containers.

## To-do

- [x] Update all pulled images
- [x] Remove all `<none>` tagged images
- [ ] Remove all stopped containers
- [ ] Lookup all available tags
