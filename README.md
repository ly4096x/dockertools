# dockertools
A small script that adds useful commands for docker

## Usage

`dockertools update-images`: Update all pulled images with respect to their tags.

`dockertools remove-none-images`: Remove all `<none>` tagged images if they are not being used by containers.

`dockertools list-tags centos`: List all tags available for `centos` image along with supported CPU arch

`dockertools snapshot-volumes [--use-compress-program '...'] <vol1 vol2 ...>|<-a|--all> <-d|--destination-dir /path/to/backup>`: Snapshot specific volumes to the destination directory. Use `-a/--all` to snapshot all volumes.

`dockertools print-volume-to-container-mappings`: Print mappings from volumes to containers they are attached to, formatted for readability.

## To-do

- [x] Update all pulled images
- [x] Remove all `<none>` tagged images
- [x] Lookup all available tags
- [ ] Remove all stopped containers
