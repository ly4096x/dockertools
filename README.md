# dockertools
A small script that adds useful commands for docker

## Usage

`dockertools update-images`: Update all pulled images with respect to their tags.

`dockertools remove-none-images`: Remove all `<none>` tagged images if they are not being used by containers.

`dockertools list-tags centos`: List all tags available for `centos` image along with supported CPU arch

## To-do

- [x] Update all pulled images
- [x] Remove all `<none>` tagged images
- [ ] Remove all stopped containers
- [x] Lookup all available tags
