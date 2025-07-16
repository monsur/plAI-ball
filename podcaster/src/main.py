from podcaster.src import args_helper, archive, audio, data, prompt, rss, transcript

def main():
    args = args_helper.get_args()
    filecount = data.run(args)
    if (filecount == 0):
        return
    prompt.run(args)
    transcript.run(args)
    audio.run(args)
    rss.run(args)
    archive.run(args)

if __name__ == "__main__":
    main()
