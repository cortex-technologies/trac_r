This project uses the following rules:

always use 
uv run <filename>.py [but if it is a training script or something heavy ask me to do it]
uv add <package-name>
`uv run ruff check && uv run ruff format --check && uv run ty check` to check if things will run..
try to avoid `Any` type

write all the final "architecture" into /doc folder. several system parts might have different files. if a system is big it might have multiples files. do not keep the intermideate version here, rather keep the full cleaned final architecture as a .md file in this folder
