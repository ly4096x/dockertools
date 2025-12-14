import sys, os, subprocess

def get_timestamp_str(image):
    subprocess.run(f'docker pull {image}'.split(' '), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    r = subprocess.run(f"docker image inspect {image}".split(' ') + ['--format', r'{{.Created}}'], check=True, capture_output=True)
    r = r.stdout.decode('utf-8').split('.')[0]
    r = ''.join(r.split(':'))
    r = ''.join(r.split('-'))
    r = '_'.join(r.split('T'))
    return r

if __name__ == '__main__':
    images = []
    try:
        with open(sys.argv[1], 'r') as f:
            for line in f.readlines():
                if line.startswith('FROM '):
                    line = [s for s in line.split() if s]
                    images += [line[1]]
    except FileNotFoundError:
        print(f"Error: Dockerfile not found at {sys.argv[1]}")
        # Assuming failure means we should probably build or just exit 1. 
        # But if the action fails, the workflow might fail. 
        # For safety, let's output 1 (update needed/unknown state) so we don't block.
        print(f'::set-output name=result::1')
        sys.exit(0)

    print('Checking image', os.environ['package_tag'])
    ref_timestamp = '00000000_000000'
    try:
        ref_timestamp = get_timestamp_str(os.environ['package_tag'])
    except:
        print(f"Could not fetch timestamp for {os.environ['package_tag']}, assuming new.")
        pass
    print('Latest package T=', ref_timestamp, sep='')

    ret = 0
    for image in images:
        print('Checking image', image, '... ', end='')
        try:
            r = get_timestamp_str(image)
            if r > ref_timestamp:
                print('has an update, T=', r, sep='')
                ret = 1
            else:
                print('no update, T=', r, sep='')
        except Exception as e:
            print(f"Failed to check image {image}: {e}")
            ret = 1 # Fail open (build)

    print(f'::set-output name=result::{ret}')
    
    # 0 = no update
    # 1 = has update
    sys.exit(0)
